from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from db_config import SECRET_KEY
from datetime import datetime, timedelta
import jwt, re



db = SQLAlchemy()
ma = Marshmallow()
bcrypt = Bcrypt()
migrate = Migrate()  


def create_token(user_id):
    """
    Creates a JSON Web Token (JWT) for the given user ID.

    Parameters:
    - user_id (str): The ID of the user.

    Returns:
    - str: The generated JWT.
    """
    payload = {
        'exp': datetime.utcnow() + timedelta(days=4),
        'iat': datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm='HS256'
    )

def extract_auth_token(authenticated_request):
    """
    Extracts the authentication token from the given authenticated request.

    Parameters:
    - authenticated_request (object): The authenticated request object.

    Returns:
    - str or None: The extracted authentication token, or None if not found.
    """
    auth_header = authenticated_request.headers.get('Authorization')
    if auth_header:
        return auth_header.split(" ")[1]
    else:
        return None

def decode_token(token):
    """
    Decode a JWT token and return the subject (sub) claim.

    Parameters:
    - token (str): The JWT token to decode.

    Returns:
    - str: The subject (sub) claim extracted from the token.

    Raises:
    - jwt.exceptions.InvalidTokenError: If the token is invalid or cannot be decoded.
    """
    payload = jwt.decode(token, SECRET_KEY, 'HS256')
    return payload['sub']


# Check if the user_name is in valid format

def validate_username_format(user_name):
    """
    Validates the format of a username.

    Parameters:
    - user_name (str): The username to be validated.

    Returns:
    - bool: True if the username format is valid, False otherwise.
    """
    pattern = re.compile(r'\s')
    return re.match(pattern, user_name) is not None

# Check if the email is in valid format
def validate_email(email):
    """
    Validates if the given email address is in a valid format.

    Parameters:
    - email (str): The email address to be validated.

    Returns:
    - bool: True if the email address is valid, False otherwise.
    """
    email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    return re.match(email_pattern, email) is not None

# Check if the password meets the required complexity
def validate_password(password):
    """
    Validates a password based on the following criteria:
    - Length of the password must be at least 8 characters
    - Password must contain at least one lowercase letter
    - Password must contain at least one uppercase letter
    - Password must contain at least one digit
    - Password must contain at least one special symbol (non-alphanumeric character)

    Parameters::
    - password (str): The password to be validated.

    Returns:
    - bool: True if the password is valid, False otherwise.
    """
    lowercase_pattern = re.compile(r'[a-z]')
    uppercase_pattern = re.compile(r'[A-Z]')
    number_pattern = re.compile(r'\d')
    special_symbol_pattern = re.compile(r'[^a-zA-Z0-9]')

    return (
        len(password) >= 8 and
        lowercase_pattern.search(password) is not None and
        uppercase_pattern.search(password) is not None and
        number_pattern.search(password) is not None and
        special_symbol_pattern.search(password) is not None
    )
