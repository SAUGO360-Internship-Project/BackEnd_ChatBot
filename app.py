import sys
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import text
from flask_migrate import Migrate


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
from utils import get_embeddings, cosine_similarity, select_relevant_few_shots  # Import utility functions
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

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_sql_query(user_question):
    few_shot_examples = FewShot.query.all()
    relevant_examples = select_relevant_few_shots(user_question, few_shot_examples)

    example_texts = "\n".join(
        [f"Question: \"{ex.question}\"\nSQL: \"{ex.sql_query}\"" for ex in relevant_examples]
    )
    
    prompt = f"""
    The database schema is as follows:
    (Provide your schema information here when ready)

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

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_question = data.get('question')
    chat_id = data.get('chat_id')  # Added chat_id to identify the conversation
    if not user_question or not chat_id:
        return jsonify({"error": "Question and chat_id are required"}), 400

    # Generate SQL query
    sql_query = generate_sql_query(user_question)

    try:
        # Execute SQL query
        result = db.session.execute(text(sql_query)).fetchall()
        result_dicts = [dict(row) for row in result]

        # Format the result with GPT-4
        formatted_response = format_response_with_gpt(user_question, result_dicts)
        
        # Store the conversation
        conversation = Conversation(chat_id=chat_id, user_query=user_question, response=formatted_response)
        db.session.add(conversation)
        db.session.commit()

        return jsonify({"response": formatted_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return (
        "Welcome to the Intelligent Chatbot with PostgreSQL home page"
        "ChatBot API Documentation Link: "
    )



if __name__ == '__main__':
    app.run(debug=True)
