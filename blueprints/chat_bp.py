from flask import Blueprint, request, jsonify
from openai import OpenAI
from model.chat import Chat, Conversation, chat_schema, chats_schema, conversation_schema, conversations_schema
from extensions import db
import os

# Initialize the blueprint
chat_bp = Blueprint('chat_bp', __name__)

# Initialize the OpenAI client with the API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# Endpoint to create a new chat
@chat_bp.route('/chats', methods=['POST'])
def create_chat():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({"error": "Title is required"}), 400

        chat = Chat(title=title)
        db.session.add(chat)
        db.session.commit()

        return jsonify(chat_schema.dump(chat))
    except Exception as e:
        print(f"Error creating chat: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


# Endpoint to get all conversations for a chat
@chat_bp.route('/chats/<int:chat_id>/conversations', methods=['GET'])
def get_conversations(chat_id):
    try:
        conversations = Conversation.query.filter_by(chat_id=chat_id).all()
        return jsonify(conversations_schema.dump(conversations))
    except Exception as e:
        print(f"Error retrieving conversations: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Endpoint to get all chats
@chat_bp.route('/chats', methods=['GET'])
def get_all_chats():
    try:
        chats = Chat.query.all()
        return jsonify(chats_schema.dump(chats))
    except Exception as e:
        print(f"Error retrieving chats: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
