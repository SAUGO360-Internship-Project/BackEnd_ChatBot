import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from flask import Flask
from flask_cors import CORS
from extensions import db, ma, bcrypt, migrate
from model.user import User, user_schema
from db_config import DB_CONFIG

from blueprints.user_bp import user_bp




app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Initialize CORS
CORS(app)

# Initialize Flask extensions
db.init_app(app)
ma.init_app(app)
bcrypt.init_app(app)
migrate.init_app(app, db)  # Initialize Flask-Migrate

app.register_blueprint(user_bp)


@app.route('/')
def home():
    return (
    "Welcome to the Intelligent Chatbot with PostgreSQL home page"
    "ChatBot API Documentation Link: "
    
)

# Register routes
@app.route('/hello', methods=['GET'])
def hello_world():
    return "Hello World!"

if __name__ == '__main__':
    app.run(debug=True)
