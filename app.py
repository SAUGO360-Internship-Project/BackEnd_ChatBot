import sys
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import text
from flask_migrate import Migrate
from datetime import datetime

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import extensions
from extensions import db, ma, bcrypt, migrate
from model.user import User, user_schema
from blueprints.user_bp import user_bp
from blueprints.chat_bp import chat_bp
from blueprints.fewshot_bp import fewshot_bp  # Import fewshot_bp
from model.chat import Chat, Conversation, chat_schema, conversation_schema
from model.few_shot import FewShot
from extensions import extract_name_from_question, fetch_address_and_generate_link, generate_sql_query,format_response_with_gpt 
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

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(chat_bp, url_prefix='/chat')
app.register_blueprint(fewshot_bp, url_prefix='/fewshot')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_question = data.get('question')
    chat_id = data.get('chat_id')  # Added chat_id to identify the conversation
    if not user_question or not chat_id:
        return jsonify({"error": "Question and chat_id are required"}), 400
    
     # Check if the question is about location
    if any(keyword in user_question.lower() for keyword in ["location", "address", "where", "located"]):
        name = extract_name_from_question(user_question)
        if not name:
            return jsonify({"error": "Could not determine the name from the question"}), 400
        maps_link = fetch_address_and_generate_link(name)
        if not maps_link:
            return jsonify({"error": "Could not find the address for the specified person"}), 404
        return jsonify({"response": f"The address for {name} is: {maps_link}"})

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
