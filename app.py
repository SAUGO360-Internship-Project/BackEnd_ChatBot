import sys
import os, re
# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import text
from flask_migrate import Migrate
from datetime import datetime
import numpy as np
import googlemaps
from openai import OpenAI



# Import extensions
from extensions import db, ma, bcrypt, migrate
from model.user import User, user_schema
from blueprints.user_bp import user_bp
from blueprints.chat_bp import chat_bp
from blueprints.fewshot_bp import fewshot_bp  # Import fewshot_bp
from model.chat import Chat, Conversation, chat_schema, conversation_schema
from model.few_shot import FewShot
from model.test import CustomerProfile, Product, PurchaseHistory

# Load environment variables
load_dotenv()

DB_CONFIG = os.getenv('DB_CONFIG')
DB_CONFIG_TEST = os.getenv('DB_CONFIG_TEST')


app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
app.config['SQLALCHEMY_BINDS'] = {
    'TestingData': DB_CONFIG_TEST
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize CORS
CORS(app)

# Initialize Flask extensions
db.init_app(app)
ma.init_app(app)
bcrypt.init_app(app)
# Initialize Flask-Migrate for the main database
migrate_main = Migrate(app, db, directory='migrations')

# Initialize Flask-Migrate for the test database
migrate_test = Migrate(app, db, directory='migrations_test')

#Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Initialize Google Maps client
# gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(chat_bp, url_prefix='/chat')
app.register_blueprint(fewshot_bp, url_prefix='/fewshot')

# Load the database schema prompt from a file
with open('db_schema_prompt.txt', 'r') as file:
    db_schema_prompt = file.read()

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
    {db_schema_prompt}
    
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
# def get_google_maps_link(address):
#     # Geocoding an address
#     geocode_result = gmaps.geocode(address)

#     if geocode_result:
#         lat = geocode_result[0]['geometry']['location']['lat']
#         lng = geocode_result[0]['geometry']['location']['lng']
#         google_maps_link = f"https://www.google.com/maps?q={lat},{lng}"
#         return google_maps_link
#     else:
#         return None
   
#function to fetch the locations from the database and generate a link to google maps
# def fetch_address_and_generate_link(name):
#     try:
#         # Get the appropriate session with the bind key
#         engine = db.get_engine(app, bind='TestingData')
#         session = engine.connect()

#         customer = CustomerProfile.query.filter_by(first_name=name).first()
#         if not customer:
#             return None
        
#         address = f"{customer.address}, {customer.city}, {customer.state}, {customer.zip_code}"
        
#         google_maps_link = get_google_maps_link(address)
        
#         return {"address": address, "google_maps_link": google_maps_link}
        
#     except Exception as e:
#         print(f"Error: {e}")
#         return None
#     finally:
#         session.close()
        
#function to exctract the name from the question
def extract_name_from_question(question):
    # Simple regex to extract a name (assuming the name is a single word, adjust as necessary)
    match = re.search(r'\b[A-Z][a-z]*\b', question)
    return match.group(0) if match else None

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_question = data.get('question')
    chat_id = data.get('chat_id')  # Added chat_id to identify the conversation
    if not user_question or not chat_id:
        return jsonify({"error": "Question and chat_id are required"}), 400
    
     # Check if the question is about location
    # if any(keyword in user_question.lower() for keyword in ["location", "address", "where", "located"]):
    #     name = extract_name_from_question(user_question)
    #     if not name:
    #         return jsonify({"error": "Could not determine the name from the question"}), 400
    #     maps_link = fetch_address_and_generate_link(name)
    #     if not maps_link:
    #         return jsonify({"error": "Could not find the address for the specified person"}), 404
    #     return jsonify({"response": f"The address for {name} is: {maps_link}"})

    # Generate SQL query
    sql_query = generate_sql_query(user_question)

    try:
        # Get the appropriate session with the bind key
        engine = db.get_engine(app, bind='TestingData')
        session = engine.connect()
        
        # Execute SQL query on TestingData
        result = session.execute(text(sql_query)).fetchall() 

        # Debugging: Print the result to verify structure
        print(f"SQL Query Result: {result}") 


        # Format the result with GPT-4
        formatted_response = format_response_with_gpt(user_question, result)
        
        # Store the conversation
        conversation = Conversation(chat_id=chat_id, user_query=user_question, response=formatted_response)
        db.session.add(conversation)
        db.session.commit()

        return jsonify({"response": formatted_response}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/')
def home():
    return (
        "Welcome to the Intelligent Chatbot with PostgreSQL home page"
        "ChatBot API Documentation Link: "
    )


if __name__ == '__main__':
    app.run(debug=True)
