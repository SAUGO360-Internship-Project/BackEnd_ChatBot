from flask import Blueprint, request, jsonify
import pyotp
import qrcode
from model.user import User, user_schema
from extensions import db, bcrypt, validate_email, validate_password, validate_username_format, extract_auth_token, decode_token, create_token, verify_otp

user_bp = Blueprint('user_bp', __name__)

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
        #qrcode.make(qr_code_url).save("totp.png")
        
        # Serialize the new user object
        serialized_user = user_schema.dump(new_user)

        # Add QR code URL to the serialized user data
        serialized_user['qr_code_url'] = qr_code_url
        
        # Return the serialized user data
        return jsonify(serialized_user), 201

    except Exception as e:
        return jsonify({"message": str(e)}), 400
        
        
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
    
    
