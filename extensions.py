from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from datetime import datetime, timedelta
import jwt, re
import os
import pyotp
from openai import OpenAI
import numpy as np
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from chromadb.config import Settings
import googlemaps
import json
from dotenv import load_dotenv
import pdfplumber
import pytesseract
from PIL import Image
from werkzeug.utils import secure_filename
from email.message import EmailMessage
import smtplib
from email.utils import formataddr
from langchain.text_splitter import RecursiveCharacterTextSplitter
import hashlib



load_dotenv()

ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'uploads/'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
EMAIL = os.getenv('EMAIL')
PASS = os.getenv('PASS')

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
#function to verify phone number 
def validate_phone_number(phone_number):
    """
    Validates a phone number using a regular expression pattern.

    Parameters:
    - phone_number (str): The phone number to be validated.

    Returns:
    - bool: True if the phone number is valid, False otherwise.
    """
    pattern = r'^\+961\d{8}$'
    return re.match(pattern, phone_number) is not None

# Verify OTP during login
def verify_otp(user, otp):
    """
    Verify the given OTP for a user.

     Parameters:
    - user (User): The user object.
    - otp (str): The OTP to verify.

    Returns:
    - bool: True if the OTP is valid, False otherwise.
    """
    totp = pyotp.TOTP(user.secret_key)
    return totp.verify(otp)


def send_email (token, recipient, user_name):
    """
    Sends an email with a reset code to the specified recipient.

    Parameters:
    - token (str): The reset code to be included in the email.
    - recipient (str): The email address of the recipient.
    - user_name (str): The name of the user receiving the reset code.

    Returns:
    - None
    """ 
    # Define the sender's name and email address
    sender_name = "Intelligent Chatbot IT Team"
    sender_email = EMAIL

    # Format the sender's name and email address
    formatted_sender = formataddr((sender_name, sender_email))
    
    sender = EMAIL
    recipient = recipient
    
    message = f'Dear {user_name}, \n\nYour Chatbot account reset code is: {token}\n\nMake sure not to forget your password again\n\nBest regards,\n\nIntelligent Chatbot IT Team\n'

    email = EmailMessage()
    # email["From"] = sender
    email['From'] = formatted_sender
    email["To"] = recipient
    email["Subject"] = "Your Intelligent Chatbot reset code"
    email.set_content(message)

    smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
    smtp.starttls()
    smtp.login(sender, PASS)
    smtp.sendmail(sender, recipient, email.as_string())
    smtp.quit()

    
def change_password_email (recipient, user_name):

    # Define the sender's name and email address
    sender_name = "Intelligent Chatbot Security Team"
    sender_email = EMAIL

    # Format the sender's name and email address
    formatted_sender = formataddr((sender_name, sender_email))
    
    sender = EMAIL
    recipient = recipient
    
    message = f'Dear {user_name}, \n\nWe wanted to inform you that your password has been successfully changed. If you did not initiate this change, please notify us immediately so we can investigate further and take necessary security measures. \n\nBest regards,\n\nIntelligent Chatbot Security Team\n'

    email = EmailMessage()
    # email["From"] = sender
    email['From'] = formatted_sender
    email["To"] = recipient
    email["Subject"] = "Important: Password Change Notification"
    email.set_content(message)

    smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
    smtp.starttls()
    smtp.login(sender, PASS)
    smtp.sendmail(sender, recipient, email.as_string())
    smtp.quit()

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
    address_data = result
    address_parts = [str(part) for part in address_data if part]
    print(", ".join(address_parts))
    return ", ".join(address_parts)

# Helper function to get Google Maps coordinates
def get_google_maps_loc(address):
    if not address:
        return None
    
    def attempt_geocode(addr_parts):
        addr = ", ".join(addr_parts)
        try:
            geocode_result = gmaps.geocode(addr)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                print(location)
                return location['lat'], location['lng']
        except Exception as e:
            print(f"Error geocoding address {addr}: {e}")
        return None

    address_parts = address.split(", ")
    for i in range(len(address_parts)):
        result = attempt_geocode(address_parts[i:])
        if result is not None:
            return result
    
    print("Could not geocode address with any combination.")
    return None




def format_as_table(results, keys):
    table = '<table border="1">\n<tr>'
    # Create table header
    for key in keys:
        table += f'<th>{key}</th>'
    table += '</tr>\n'
    # Create table rows
    for row in results:
        table += '<tr>'
        for value in row:
            table += f'<td>{value}</td>'
        table += '</tr>\n'
    table += '</table>'
    return table



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


def generate_map_code(coordinates, map_type, base_code):
    if map_type=="GoogleMaps":
        map_type="normal"
    elif map_type=="TriangleMaps":
        map_type="triangle"
    coordinates_str = json.dumps(coordinates)
    return base_code\
        .replace("{coordinates}", coordinates_str)\
        .replace("{type}", f"'{map_type}'")


def generate_heatmap_code(xlabels, ylabels, heatmapdata, base_code):

    return base_code\
        .replace("{xLabels}", f'{xlabels}')\
        .replace("{yLabels}", f'{ylabels}')\
        .replace("{heatMapData}", f'{heatmapdata}')




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_pdf(filename, user_id):
    if not filename or not user_id:
        return {"message": "Filename and user_id are required"}, 400

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return {"message": "File not found"}, 404

    collection_name = f"user_{user_id}_pdfs"
    result_message = chunk_pdf_to_chroma(filename,file_path, collection_name)

    return {"message": result_message}, 200
def extract_text_with_ocr(page):
    images = page.images
    if images:
        texts = []
        for img in images:
            with page.within_bbox(img["bbox"]) as region:
                pil_image = region.to_image(resolution=300).original
                text = pytesseract.image_to_string(pil_image)
                texts.append(text)
        return "\n".join(texts)
    return ""


def chunk_pdf_to_chroma(filename,file_path, collection_name, chunk_size=800, chunk_overlap=200):
    # Read PDF and chunk it
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if not page_text:
                page_text = extract_text_with_ocr(page)  # Use OCR if no text is found
            if page_text:
                text += page_text + "\n"  # Combine all text from the PDF

    # Use RecursiveCharacterTextSplitter to chunk the text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap,
        separators=[
        "\n\n",
        "\n",
        " ",
        ".",
        ""
        ])
    chunks = splitter.split_text(text)

    # Create or get Chroma collection
    collection = client_chroma.get_or_create_collection(name=collection_name, embedding_function=openai_ef)
    title, description = get_title_and_description(text)         
    doc_id = hashlib.md5(text.encode('utf-8')).hexdigest()

    # Store chunks in Chroma collection
    for chunk_num, chunk_text in enumerate(chunks):
        collection.add(
            ids=[f"{doc_id}_chunk{chunk_num}"],
            embeddings=[get_embeddings(chunk_text)],
            metadatas=[{'filename':filename,'doc_id': doc_id,'pdf_title': title, 'description': description, 'chunk_number': chunk_num, 'chunk_text': chunk_text}]
        )

    return f"Successfully processed and stored {len(chunks)} chunks from {file_path} in Chroma collection '{collection_name}'"


def get_title_and_description(text):
    message=[{'role':'system','content':
              '''
              The user will give you text. You must generate a meaningful brief title and a brief description that is around 2 or 3 sentences as a JSON string in the following format:
              {
                'Title':
                'Description':
              }
              '''}]
    message.append({'role':'user','content':f'{text}'})
    response = client.chat.completions.create(
        model='gpt-4o',  
        messages=message,
        response_format={ "type": "json_object" }, 
        max_tokens=500
    )
    result=response.choices[0].message.content.strip()
    try:
        response_json = json.loads(result)
        title = response_json["Title"]
        description = response_json["Description"]
    except json.JSONDecodeError:
        title = None
        description = None
    return title, description



def select_relevant_pdf_chunks(user_question, user_id,doc_id, top_n=5, distance_threshold=1.0):
    user_embedding = get_embeddings(user_question)
    relevant_chunks = []

    # Get the user-specific PDF collection
    collection_name = f"user_{user_id}_pdfs"
    collection = client_chroma.get_collection(name=collection_name, embedding_function=openai_ef)
    if not collection:
        return "No PDFs found for this user."

    # Query the collection for the most relevant chunks
    results = collection.query(
        query_embeddings=[user_embedding],
        n_results=top_n,
        where={'doc_id':doc_id},
        include=['distances', 'metadatas']
    )

    for distances, metadata_list in zip(results['distances'], results['metadatas']):
        for distance, metadata in zip(distances, metadata_list):
            print(distance)
            if distance < distance_threshold:
                relevant_chunks.append({
                    "ids": metadata.get('ids'),
                    "pdf_title": metadata.get('pdf_title'),
                    "chunk_text": metadata.get('chunk_text'),
                    "chunk_number": metadata.get('chunk_number')
                    })

    relevant_chunks = sorted(relevant_chunks, key=lambda x: x['chunk_number'])


    return relevant_chunks
