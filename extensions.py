from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from model.few_shot import FewShot
from model.test import CustomerProfile
import googlemaps
from datetime import datetime, timedelta
import jwt, re
import os
from app import app
import numpy as np
from openai import OpenAI


SECRET_KEY= os.getenv('SECRET_KEY')
#Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Initialize Google Maps client
gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))

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



def get_embeddings(text):
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding 

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def select_relevant_few_shots(user_question, few_shot_examples, top_n=3):
    user_embedding = get_embeddings(user_question)
    similarities = []

    for example in few_shot_examples:
        example_embedding = get_embeddings(example.question)
        similarity = cosine_similarity(user_embedding, example_embedding)
        similarities.append((example, similarity))

    # Sort examples by similarity and select top_n
    similarities.sort(key=lambda x: x[1], reverse=True)
    relevant_examples = [ex[0] for ex in similarities[:top_n]]
    return relevant_examples

def generate_sql_query(user_question):
    few_shot_examples = FewShot.query.all()
    relevant_examples = select_relevant_few_shots(user_question, few_shot_examples)

    example_texts = "\n".join(
        [f"Question: \"{ex.question}\"\nSQL: \"{ex.sql_query}\"" for ex in relevant_examples]
    )

    prompt = f"""
    The database schema is as follows:

    Table customer_profile:
    - customer_id (Integer, Primary Key)
    - first_name (String)
    - last_name (String)
    - gender (String)
    - date_of_birth (Date)
    - email (String)
    - phone_number (String)
    - signup_date (Date)
    - address (String)
    - city (String)
    - state (String)
    - zip_code (String)

    Table products:
    - product_id (Integer, Primary Key)
    - product_name (String)
    - category (String)
    - price_per_unit (Float)
    - brand (String)
    - product_description (Text)

    Table purchase_history:
    - purchase_id (Integer, Primary Key)
    - customer_id (Integer, Foreign Key to customer_profile.customer_id)
    - product_id (Integer, Foreign Key to products.product_id)
    - purchase_date (Date)
    - quantity (Integer)
    - total_amount (Float)

    Examples:
    {example_texts}

    Convert the following question to a single SQL query without any additional text or explanation: "{user_question}"
    """
    
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[{"role": "system", "content": prompt}],
        max_tokens=150
    )
    sql_query = response.choices[0].message.content.strip()

    # Remove any non-SQL parts (e.g., markdown or explanations)
    if "```sql" in sql_query:
        sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
    
    return sql_query


def format_response_with_gpt(user_question, data):
    prompt = f"""
    Question: {user_question}
    
    Data: {data}
    
    Format this data in a user-friendly way:
    """
    
    response = client.chat.completions.create(
        model='gpt-4o',  # Use GPT-4 model
        messages=[{"role": "system", "content": prompt}],
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

#funciton to form the address link 
def get_google_maps_link(address):
    # Geocoding an address
    geocode_result = gmaps.geocode(address)

    if geocode_result:
        lat = geocode_result[0]['geometry']['location']['lat']
        lng = geocode_result[0]['geometry']['location']['lng']
        google_maps_link = f"https://www.google.com/maps?q={lat},{lng}"
        return google_maps_link
    else:
        return None
   
#function to fetch the locations from the database and generate a link to google maps
def fetch_address_and_generate_link(name):
    try:
        # Get the appropriate session with the bind key
        engine = db.get_engine(app, bind='TestingData')
        session = engine.connect()

        customer = CustomerProfile.query.filter_by(first_name=name).first()
        if not customer:
            return None
        
        address = f"{customer.address}, {customer.city}, {customer.state}, {customer.zip_code}"
        
        google_maps_link = get_google_maps_link(address)
        
        return {"address": address, "google_maps_link": google_maps_link}
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        session.close()
        
#function to exctract the name from the question
def extract_name_from_question(question):
    # Simple regex to extract a name (assuming the name is a single word, adjust as necessary)
    match = re.search(r'\b[A-Z][a-z]*\b', question)
    return match.group(0) if match else None