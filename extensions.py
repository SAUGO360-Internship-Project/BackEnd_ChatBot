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

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# def select_relevant_few_shots(user_question, few_shot_examples, top_n=3):
#     user_embedding = get_embeddings(user_question)
#     similarities = []

#     for example in few_shot_examples:
#         example_embedding = get_embeddings(example.question)
#         similarity = cosine_similarity(user_embedding, example_embedding)
#         similarities.append((example, similarity))

#     # Sort examples by similarity and select top_n
#     similarities.sort(key=lambda x: x[1], reverse=True)
#     relevant_examples = [ex[0] for ex in similarities[:top_n]]
#     return relevant_examples

def select_relevant_few_shots(user_question, top_n=5):
    user_embedding = get_embeddings(user_question)
    relevant_examples = []
    results = collection.query(
        query_embeddings=[user_embedding],
        n_results=top_n,
        include=['metadatas']
    )    
    for metadata_list in results['metadatas']:  # Loop through each list of metadatas
        for metadata in metadata_list:  # Loop through each metadata dictionary
            relevant_examples.append({
                "question": metadata.get('question'),
                "sql_query": metadata.get('sql_query')
            })
    return relevant_examples
#function to exctract the name from the question
def extract_name_from_question(question):
    # Simple regex to extract a name (assuming the name is a single word, adjust as necessary)
    match = re.search(r'\b[A-Z][a-z]*\b', question)
    return match.group(0) if match else None

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