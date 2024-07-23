from flask import Blueprint, request, jsonify, send_from_directory
import pyotp
import qrcode
import jwt
from PIL import Image
from io import BytesIO
import base64
import os
from model.user import User, user_schema
from extensions import db, bcrypt, validate_email, validate_password, validate_username_format, validate_phone_number ,extract_auth_token, decode_token, create_token, verify_otp, send_email, change_password_email

user_bp = Blueprint('user_bp', __name__)


UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
#route to register a new user 
@user_bp.route('/user', methods=['POST'])
def add_user():
    try:
        data = request.json

        # Ensure all required fields are present
        if ('user_name' not in data or 'password' not in data or 'email' not in data):
            return jsonify({"message": "The user was not added. 'user_name', 'password', and 'email' are required."}), 400

        # Extract data from JSON
        user_name = data['user_name']
        email = data['email']
        password = data['password']

        # Validate the data types of the required fields
        if (not isinstance(user_name, str) or not isinstance(password, str) or 
            not isinstance(email, str)):
            return jsonify({"message": "The user was not added. 'user_name', 'password', and 'email' should be of string type."}), 400
        
        # Ensure all required fields are not null
        if user_name == "" or password == "" or email == "":
            return jsonify({"message": "Values of 'user_name', 'password', and 'email' cannot be empty."}), 400
        
        if validate_username_format(user_name):
            return jsonify({"message": "Username cannot contain spaces."}), 400

        if not validate_email(email):
            return jsonify({"message": "Invalid email format."}), 400
        
        if not validate_password(password):
            return jsonify({"message": "Password should contain at least 8 characters, including lowercase letters, uppercase letters, numbers, and special symbols."}), 400
        
        # Check if the username or email is already used
        if User.query.filter((User.user_name == user_name) | (User.email == email)).first():
            return jsonify({"message": "Username or email already used!"}), 400

         # Generate secret key and enable 2FA for the user
        secret_key = pyotp.random_base32()
        new_user = User(user_name=user_name, email=email, password=password, secret_key=secret_key)
        db.session.add(new_user)
        db.session.commit()

        # Get QR code URL for the user
        qr_code_url = pyotp.TOTP(new_user.secret_key).provisioning_uri(new_user.email, issuer_name="Intelligent Chatbot")
        # qrcode.make(qr_code_url).save("totp.png")
        
        # Serialize the new user object
        serialized_user = user_schema.dump(new_user)

        # Add QR code URL to the serialized user data
        serialized_user['qr_code_url'] = qr_code_url
        
        # Return the serialized user data
        return jsonify(serialized_user), 201

    except Exception as e:
        return jsonify({"message": str(e)}), 400
        
#route to delete the user account
@user_bp.route('/user', methods=['DELETE'])
def delete_user():
    try:

        token = extract_auth_token(request)
        if (token==None):
            return jsonify({"message": "Unauthorized"}), 401

        user_id = decode_token(token)
        if not user_id:
            return jsonify({"message": "Invalid token"}), 401

        # Check if the user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        # Delete the user
        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": "User deleted successfully."}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 400

#route to authenticate user credentials  
@user_bp.route('/authentication', methods=['POST'])
def authentication():
    try:
        data = request.json
        
        # Ensure all required fields are present
        if('user_name' not in data or 'password' not in data or 'otp' not in data):
            return jsonify({"message": "The user was not added. The 'user_name' and 'password' and 'otp' should be sent."}), 400

        # Extract data from JSON
        user_name = data['user_name']
        password = data['password']
        otp = data['otp'] 


        # Validate the data types of the required fields
        if (not isinstance(user_name, str)  or not isinstance(password, str)):
            return jsonify({"message": "The user was not authenticated. The 'user_name' and the 'password' should be of string type."}), 400
        
        # Ensure all required fields are not null
        if user_name=="" or password=="" or otp=="":
            return jsonify({"message": "Values of 'user_name', 'password' and 'otp' cannot be empty"}), 400
        
        user = User.query.filter_by(user_name=user_name).first()
        if user:
            if bcrypt.check_password_hash(user.hashed_password, password):
                if verify_otp(user, otp):
                    token = create_token(user.id)
                    return jsonify({"token": token})
                else:
                    return jsonify({"message": "Invalid OTP."}), 401 
            else:
                return jsonify({"message": "Username and Password do not match."}), 401
        else:
            return jsonify({"message": "Username and Password do not match."}), 401

    except Exception as e:
        return jsonify({"message": str(e)}), 400
    
#route to request the user's token for forgotten passwords
@user_bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    try:
        data = request.json
        if 'user_name' not in data:
            return jsonify({"message": "Username is required."}), 400
        
        user_name = data['user_name']
        if not user_name:
            return jsonify({"message": "Username is required."}), 400

        user = User.query.filter_by(user_name=user_name).first()
        if user:
            # Generate the token for the user
            token = create_token(user.id)
            email = user.email

            # Send the password reset email
            send_email(token, email, user.user_name)
            return jsonify({"message": "Password reset code sent to your email."}), 200
        else:
            return jsonify({"message": "No user found with that username."}), 404

    except Exception as e:
        return jsonify({"message": str(e)}), 400

#route to reset password  
@user_bp.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.json

        if 'reset_code' not in data or 'new_password' not in data:
            return jsonify({"message": "Reset code, and new password are required."}), 400

        reset_token = data['reset_code']
        new_password = data['new_password']
        
        # Decode the reset token to get the user ID
        user_id = decode_token(reset_token)
        if not user_id:
            return jsonify({"message": "Invalid or expired reset code."}), 400

        # Fetch the user from the database
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        # Update user's password
        user.hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()

        return jsonify({"message": "Password reset successfully."}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 400
    
#route to request the user's token for lost qrcode
@user_bp.route('/lost_qrcode', methods=['POST'])
def get_qrcode():
    try:
        data = request.json

        # Ensure all required fields are present
        if 'user_name' not in data or 'password' not in data:
            return jsonify({"message": "'user_name' and 'password' should be sent."}), 400

        # Extract data from JSON
        user_name = data['user_name']
        password = data['password']

        # Validate the data types of the required fields
        if not isinstance(user_name, str) or not isinstance(password, str):
            return jsonify({"message": "The user was not authenticated. The 'user_name' and the 'password' should be of string type."}), 400
        
        # Ensure all required fields are not null
        if user_name == "" or password == "":
            return jsonify({"message": "Values of 'user_name' and 'password' cannot be empty"}), 400

        user = User.query.filter_by(user_name=user_name).first()
        if user:
            if bcrypt.check_password_hash(user.hashed_password, password):
                # Generate the token for the user
                token = create_token(user.id)
                email = user.email

                # Send the QR code reset email
                send_email(token, email, user.user_name)
                return jsonify({"message": "QR code reset code sent to your email."}), 200
            else:
                return jsonify({"message": "Username and Password do not match."}), 401
        else:
            return jsonify({"message": "No user found with that user_name or password"}), 404

    except Exception as e:
        return jsonify({"message": str(e)}), 400

#route to reset the user's qrcode and retreive it 
@user_bp.route('/get_qrcode', methods=['POST'])
def get_qr_code_url():
    try:
        data = request.json

        if 'reset_code' not in data:
            return jsonify({"message": "Reset code is required."}), 400
        
        reset_token = data['reset_code']
        
        # Decode the reset token to get the user ID
        user_id = decode_token(reset_token)
        if not user_id:
            return jsonify({"message": "Invalid or expired reset code."}), 400

        # Fetch the user from the database
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found."}), 404

        # Update user's password
        qr_code_url = pyotp.TOTP(user.secret_key).provisioning_uri(user.email, issuer_name="Intelligent Chatbot")
        qrcode.make(qr_code_url).save("totp.png")

        return jsonify({"qr_code_url": qr_code_url}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 400

@user_bp.route('/profile-image/<filename>', methods=['GET'])
def get_profile_image(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"message": str(e)}), 400

#route to get the user's profile information 
@user_bp.route('/profile', methods=['GET'])
def get_profile():
    try:
        token = extract_auth_token(request)

        if token is None:
            return jsonify({"message": "Unauthorized"}), 401
        
        user_id = decode_token(token)
        user = User.query.get(user_id)
        if user:
            result = user_schema.dump(user)
            result['profile_image'] = f"/user/profile-image/user_{user.id}_profile.png" if user.profile_image else None
            return jsonify(result)
        else:
            return jsonify({"message": "User not found"}), 404

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({"message": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"message": str(e)})

        

    
#route to change the user's password when logged in 
@user_bp.route('/profile/password', methods=['PUT'])
def change_password():
    try:
        token = extract_auth_token(request)

        if (token==None):
            return jsonify({"message": "Unauthorized"}), 403
        else:
            user_id = decode_token(token)
            
        data = request.json
        if ('current_password' not in data or 'new_password' not in data):
            return jsonify({"message": "'current_password', and 'new_password' are required."}), 400

        current_password = data['current_password']
        new_password = data['new_password']

        user = User.query.get(user_id)
        
        if user:
            if not bcrypt.check_password_hash(user.hashed_password, current_password):
                return jsonify({"message": "Current password is incorrect."}), 400

            if not validate_password(new_password):
                return jsonify({"message": "New password should contain at least 8 characters, including lowercase letters, uppercase letters, numbers, and special symbols."}), 400
            
            # Update the user's password
            user.hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            db.session.commit()
            change_password_email(user.email, user.user_name)
            return jsonify({"message": "Password updated successfully."}), 200
        else:
            return jsonify({"message": "User not found"}), 404
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"message": "Unauthorized"}), 403    
    except Exception as e:
        return jsonify({"message": str(e)}), 400
    
    
@user_bp.route('/profile', methods=['PUT'])
def update_profile():
    try:
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Unauthorized"}), 401

        user_id = decode_token(token)
        user = User.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        data = request.form  # Get form data
        files = request.files  # Get file data

        # Update the user fields if provided in the request
        if 'user_name' in data:
            new_username = data['user_name']
            if User.query.filter_by(user_name=new_username).first():
                return jsonify({"message": "New username is already taken."}), 400
            if not validate_username_format(new_username):
                return jsonify({"message": "User cannot contain spaces."}), 400
            user.user_name = new_username

        if 'email' in data:
            new_email = data['email']
            if User.query.filter_by(email=new_email).first():
                return jsonify({"message": "Email is already in use."}), 400
            if not validate_email(new_email):
                return jsonify({"message": "Invalid email format."}), 400
            user.email = new_email

        if 'phone_number' in data:
            new_phone_number = data['phone_number']
            if not validate_phone_number(new_phone_number):
                return jsonify({"message": "Invalid phone number format."}), 400
            user.phone_number = new_phone_number

        if 'gender' in data:
            user.gender = data['gender']

        if 'bio_description' in data:
            user.bio_description = data['bio_description']

        if 'address' in data:
            user.address = data['address']

        if 'profile_image' in files:
            profile_image = files['profile_image']
            if profile_image:
                filename = f"user_{user.id}_profile.png"
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                profile_image.save(image_path)
                user.profile_image = image_path

        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return jsonify({"message": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"message": str(e)}), 400