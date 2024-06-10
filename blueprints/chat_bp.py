from flask import Blueprint, request, jsonify
import openai
import os

# Initialize the blueprint
chat_bp = Blueprint('chat_bp', __name__)

# Load the OpenAI API key from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')

# Function to call GPT-4o API
def get_gpt4o_response(query):
    try:
        response = openai.ChatCompletion.create(
            model='gpt-4o',  # Specify the GPT-4o model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ],
            max_tokens=150
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Error calling OpenAI API"

# Endpoint for user queries
@chat_bp.route('/query', methods=['POST'])
def query():
    try:
        data = request.json
        user_query = data.get('query')
        response = get_gpt4o_response(user_query)
        return jsonify({"response": response})
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
