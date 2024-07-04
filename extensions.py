from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from datetime import datetime, timedelta
import jwt, re
import os
from openai import OpenAI
import numpy as np
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from chromadb.config import Settings
import googlemaps
import json


# Initialize ChromaDB client with a persistent local path
client_chroma = chromadb.PersistentClient(path="chroma_data", settings=Settings())

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=str(os.getenv('OPENAI_API_KEY')),
                model_name="text-embedding-3-large"
            )
# Get or create the collection
collection_name = "few_shot"
collection = client_chroma.get_collection(name=collection_name,embedding_function=openai_ef)


SECRET_KEY= os.getenv('SECRET_KEY')

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
        model="text-embedding-3-large",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding 


def select_relevant_few_shots(user_question, user_id, top_n_main=5, top_n_user=2, distance_threshold=1.5):
    user_embedding = get_embeddings(user_question)
    relevant_examples = []

    # Query main collection
    results_main = collection.query(
        query_embeddings=[user_embedding],
        n_results=top_n_main,
        include=['distances', 'metadatas']
    )

    for distances, metadata_list in zip(results_main['distances'], results_main['metadatas']):
        for distance, metadata in zip(distances, metadata_list):
            if distance < distance_threshold:
                relevant_examples.append({
                    "Question": metadata.get('Question'),
                    "Score": metadata.get('Score'),
                    "Executable": metadata.get('Executable'),
                    "Answer": metadata.get('Answer'),
                    "Location": metadata.get('Location'),
                    "ChartName": metadata.get('ChartName')
                })

    # Query user-specific collection
    user_collection_name = f"few_shot_user_{user_id}"
    user_collection = client_chroma.get_or_create_collection(name=user_collection_name, embedding_function=openai_ef)

    results_user = user_collection.query(
        query_embeddings=[user_embedding],
        n_results=top_n_user,
        include=['distances', 'metadatas']
    )

    for distances, metadata_list in zip(results_user['distances'], results_user['metadatas']):
        for distance, metadata in zip(distances, metadata_list):
            if distance < distance_threshold:
                relevant_examples.append({
                    "Question": metadata.get('Question'),
                    "Score": metadata.get('Score'),
                    "Executable": metadata.get('Executable'),
                    "Answer": metadata.get('Answer'),
                    "Location": metadata.get('Location'),
                    "ChartName": metadata.get('ChartName')
                })

    return relevant_examples


# Function to detect sensitive info
def contains_sensitive_info(question):
    sensitive_keywords = ['password', 'user credential', 'api key','id', 'secret', 'token', 'primary key']
    # Compile regex patterns for each keyword with word boundaries
    patterns = [re.compile(rf'\b{keyword}\b', re.IGNORECASE) for keyword in sensitive_keywords]
    return any(pattern.search(question) for pattern in patterns)



# Function to check for data-altering operations
def contains_data_altering_operations(sql_query):
    altering_keywords = ['delete', 'update', 'insert', 'alter', 'drop', 'create']
    return any(keyword in sql_query.lower() for keyword in altering_keywords)



# Helper function to format the address from the SQL result
def format_address(result):
    if not result or len(result) == 0:
        return None
    address_data = result[0]
    address_parts = [str(part) for part in address_data if part]
    print(", ".join(address_parts))
    return ", ".join(address_parts)

# Helper function to get Google Maps URL
def get_google_maps_url(address):
    if not address:
        return None
    geocode_result = gmaps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        print(location)
        lat, lng = location['lat'], location['lng']
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    return None


def format_as_table(results):
    rows = []
    for row in results:
        rows.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(rows)

def generate_chart_code(data, xlabel, ylabel, chart_name, base_code):
    chart_data = json.dumps(data, indent=2)
    chart_component_name = chart_name
    chart_component = chart_name[:-5]

    return base_code\
        .replace("{chartName}", chart_component_name)\
        .replace("{chartComponent}", chart_component)\
        .replace("{data}", chart_data)\
        .replace("{labelX}", xlabel)\
        .replace("{labelY}", ylabel)


