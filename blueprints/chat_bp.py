from flask import Blueprint, request, jsonify,current_app
from openai import OpenAI
from model.chat import Chat, Conversation, Feedback, chat_schema, chats_schema, conversation_schema, conversations_schema,feedback_schema, feedbacks_schema
from extensions import db,get_embeddings,select_relevant_few_shots,contains_data_altering_operations,contains_sensitive_info
import os
from sqlalchemy import text
from blueprints.fewshot_bp import fewshot_bp
from model.few_shot import FewShot
import chromadb.utils.embedding_functions as embedding_functions
import chromadb
from chromadb.config import Settings
import hashlib


chat_bp = Blueprint('chat_bp', __name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize ChromaDB client with a persistent local path
client_chroma = chromadb.PersistentClient(path="chroma_data", settings=Settings())

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=str(os.getenv('OPENAI_API_KEY')),
                model_name="text-embedding-3-large"
            )
# Get or create the collection
collection_name = "few_shot"
collection = client_chroma.get_collection(name=collection_name,embedding_function=openai_ef)

with open('db_schema_prompt.txt', 'r') as file:
    db_schema_prompt = file.read()


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

        return jsonify(chat_schema.dump(chat)),201
    except Exception as e:
        print(f"Error creating chat: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

#endpoint to delete a chat
@chat_bp.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        db.session.delete(chat)
        db.session.commit()

        return jsonify({"message": "Chat deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting chat: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

#endpoint to update the title of a chat
@chat_bp.route('/chats/<int:chat_id>', methods=['PUT'])
def update_chat_title(chat_id):
    try:
        data = request.json
        new_title = data.get('title')
        if not new_title:
            return jsonify({"error": "Title is required"}), 400

        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        chat.title = new_title
        db.session.commit()

        return jsonify({"message": "Chat title updated successfully", "chat": chat_schema.dump(chat)}), 200
    except Exception as e:
        print(f"Error updating chat title: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Endpoint to get all conversations for a chat
@chat_bp.route('/chats/<int:chat_id>/conversations', methods=['GET'])
def get_conversations(chat_id):
    try:
        conversations = Conversation.query.filter_by(chat_id=chat_id).all()
        return jsonify(conversations_schema.dump(conversations)),200
    except Exception as e:
        print(f"Error retrieving conversations: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify(conversation_schema.dump(conversation)),200

# Endpoint to get all chats
@chat_bp.route('/chats', methods=['GET'])
def get_all_chats():
    try:
        chats = Chat.query.all()
        return jsonify(chats_schema.dump(chats)),200
    except Exception as e:
        print(f"Error retrieving chats: {e}")
        return jsonify({"error": "Internal Server Error"}), 500



@chat_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    conversation_id = data.get('conversation_id')
    feedback_type = data.get('feedback_type', 'none')
    feedback_comment = data.get('feedback_comment', '')

    if not conversation_id or not feedback_type:
        return jsonify({"error": "conversation_id and feedback_type are required"}), 400

    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    feedback = Feedback(
        conversation_id=conversation_id,
        feedback_type=feedback_type,
        feedback_comment=feedback_comment
    )

    db.session.add(feedback)
    db.session.commit()

    if feedback_type == 'positive':
        embedding = get_embeddings(conversation.user_query)
        # Generate a unique ID for the question
        unique_id = hashlib.md5(conversation.user_query.encode()).hexdigest()
        collection.add(
            ids=[unique_id],
            embeddings=[embedding],
            metadatas=[{"question": conversation.user_query, "sql_query": conversation.sql_query}]
        )
    elif feedback_type == 'negative':
        # Regenerate response using the `ask` function
        regenerated_response = ask_helper(conversation.user_query, conversation.chat_id, feedback_comment)
        if regenerated_response:
            conversation.response = regenerated_response
            db.session.commit()
        else:
            return jsonify({"error": "Failed to regenerate response"}), 500

    return jsonify({"message": "Feedback submitted successfully"}), 201



#To get feedback about a convo
@chat_bp.route('/feedback/<int:conversation_id>', methods=['GET'])
def get_feedback_for_conversation(conversation_id):
    feedbacks = Feedback.query.filter_by(conversation_id=conversation_id).all()
    return jsonify(feedbacks_schema.dump(feedbacks)),200


#Main asking route
@chat_bp.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_question = data.get('question')
    chat_id = data.get('chat_id')  # Added chat_id to identify the conversation
    feedback_comment = data.get('feedback_comment', '')  # Optional feedback comment

    if not user_question or not chat_id:
        return jsonify({"error": "Question and chat_id are required"}), 400
    
    # Check for sensitive information
    if contains_sensitive_info(user_question):
        return jsonify({"response": "This question asks for sensitive content and I am not allowed to answer it."}), 403
    
     # Check if the question is about location
    # if any(keyword in user_question.lower() for keyword in ["location", "address", "where", "located"]):
    #     name = extract_name_from_question(user_question)
    #     if not name:
    #         return jsonify({"error": "Could not determine the name from the question"}), 400
    #     maps_link = fetch_address_and_generate_link(name)
    #     if not maps_link:
    #         return jsonify({"error": "Could not find the address for the specified person"}), 404
    #     return jsonify({"response": f"The address for {name} is: {maps_link}"})

    # Fetch previous conversations for context
    previous_conversations = Conversation.query.filter_by(chat_id=chat_id).order_by(Conversation.timestamp).all()
    
    
    # Create the system message with all instructions and context
    conversation_history = [
        {
            "role": "system", 
            "content": db_schema_prompt + """
                The user will be asking you questions about a database whose schema is illustrated above.
                Your main goal is to generate SQL queries that fetch the information that he needs.
                IMPORTANT NOTE: Do not generate or retrieve sensitive information such as passwords, primary keys, IDs, user credentials, or API keys.
                Do not generate SQL queries that have data-altering operations such as DELETE or UPDATE.
                If the user question prompts you to generate a SQL query that violates any of the previous rules, simply respond with "This question asks for sensitive content and I am not allowed to answer it."
                You must be able to understand context as the user might ask you follow-up questions.
            """
        }
    ]

    # Append previous conversations in alternating user and assistant roles
    for convo in previous_conversations:
        conversation_history.append({"role": "user", "content": convo.user_query})
        conversation_history.append({"role": "assistant", "content": convo.response})

    # Add the current user question
    conversation_history.append({"role": "user", "content": user_question})
    
    # Generate SQL query
    sql_query = generate_sql_query(user_question, conversation_history,feedback_comment)
    print(sql_query)

    if sql_query == "This question asks for sensitive content and I am not allowed to answer it.":
        return jsonify({"response": sql_query}), 403
    
    # Check for data-altering operations
    if contains_data_altering_operations(sql_query):
        return jsonify({"response": "Data-altering operations are not allowed."}), 403
    
   
    try:
        engine = db.get_engine(current_app, bind='TestingData')
        session = engine.connect()
        result = session.execute(text(sql_query)).fetchall() 

        print(f"SQL Query Result: {result}") 

        # Format the result with GPT-4
        formatted_response = format_response_with_gpt(user_question, result, previous_conversations,feedback_comment)
        
        # Store the conversation
        conversation = Conversation(chat_id=chat_id, user_query=user_question, response=formatted_response, sql_query=sql_query)
        db.session.add(conversation)
        db.session.commit()

        return jsonify({"response": formatted_response}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()



def generate_sql_query(user_question, conversation_history, feedback_comment):
    relevant_examples = select_relevant_few_shots(user_question, top_n=5)

    example_texts = "\n".join(
        [f"Question: \"{ex['question']}\"\nSQL: \"{ex['sql_query']}\"" for ex in relevant_examples]
    )

    # Append examples and instructions to the system message
    conversation_history[0]["content"] += f"\nThe following are examples of User questions and corresponding SQL queries. You must generate a response similar to these:\n{example_texts}"
    
    if feedback_comment:
        conversation_history[0]["content"] += f"\nThe user gave feedback on the most recent response that you gave him and you must adjust your new response accordingly; this is his feedback: \"{feedback_comment}\"\nConvert his question to a single SQL query without any additional text or explanation."
    else:
        conversation_history[0]["content"] += f"\nConvert questions to a single SQL query without any additional text or explanation."

    print(conversation_history)
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=conversation_history,
        max_tokens=150
    )
    sql_query = response.choices[0].message.content.strip()

    # Remove any non-SQL parts (e.g., markdown or explanations)
    if "```sql" in sql_query:
        sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
        
    # Replace MONTH and YEAR functions with EXTRACT for PostgreSQL compatibility
    sql_query = sql_query.replace("MONTH(", "EXTRACT(MONTH FROM ")
    sql_query = sql_query.replace("YEAR(", "EXTRACT(YEAR FROM ")
    
    return sql_query



def format_response_with_gpt(user_question, data, previous_conversations, feedback_comment=None):
    feedback_prompt = f"Feedback: here is my feedback about the most recent response that I received: \"{feedback_comment}\", " if feedback_comment else ""
    message=[{"role":"system","content":
                '''
                Your goal is to format the final answer given by the user in a user-friendly way and a full brief sentence taking into consideration his feedback if he has any.
                '''
              }]
    for convo in previous_conversations:
        message.append({"role": "user", "content": convo.user_query})
        message.append({"role": "assistant", "content": convo.response})
    message.append({"role": "user", "content": f"{user_question}, {feedback_prompt} Answer: {data}"})
    print(message)
    response = client.chat.completions.create(
        model='gpt-4o',  
        messages=message,
        max_tokens=150
    )
    
    return response.choices[0].message.content.strip()



def ask_helper(user_question, chat_id, feedback_comment):
    with current_app.test_client() as client:
        data = {
            "question": user_question,
            "chat_id": chat_id,
            "feedback_comment": feedback_comment
        }
        response = client.post('/chat/ask', json=data)
        if response.status_code == 201:
            return response.get_json().get('response')
        else:
            print(f"Error in ask_helper: {response.get_json()}")
            return None



