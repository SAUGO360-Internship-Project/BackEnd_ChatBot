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
from extensions import db, ma, bcrypt, migrate, get_embeddings,cosine_similarity,select_relevant_few_shots,extract_name_from_question,contains_sensitive_info,contains_data_altering_operations
from model.user import User, user_schema
from blueprints.user_bp import user_bp
from blueprints.chat_bp import chat_bp,generate_sql_query,format_response_with_gpt
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
        


@app.route('/')
def home():
    return (
        "Welcome to the Intelligent Chatbot with PostgreSQL home page"
        "ChatBot API Documentation Link: "
    )


if __name__ == '__main__':
    app.run(debug=True)
