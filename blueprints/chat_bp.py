from flask import Blueprint, request, jsonify,current_app
from openai import OpenAI
from model.chat import Chat, Conversation, Feedback, chat_schema, chats_schema, conversation_schema, conversations_schema,feedback_schema, feedbacks_schema
from extensions import db,get_embeddings,select_relevant_few_shots,contains_data_altering_operations,contains_sensitive_info,get_google_maps_loc,format_address,create_token,extract_auth_token,decode_token,format_as_table,generate_chart_code,generate_map_code,generate_heatmap_code
import os
from sqlalchemy import text
from blueprints.fewshot_bp import fewshot_bp
import chromadb.utils.embedding_functions as embedding_functions
import chromadb
from chromadb.config import Settings
import hashlib
import json


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

with open('chart_code.txt', 'r') as file:
    chart_base_code = file.read()

with open('map_code.txt', 'r') as file:
    map_base_code = file.read()

with open('heat_code.txt', 'r') as file:
    heat_base_code = file.read()

# Create a chat
@chat_bp.route('/chats', methods=['POST'])
def create_chat():
    try:
        data = request.json
        title = data.get('title')
        
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        try:
            user_id = decode_token(token)
        except Exception as e:
            print(f"Error decoding token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        if not title or not user_id:
            return jsonify({"message": "Title and user_id are required"}), 400

        new_chat = Chat(title=title, user_id=user_id)
        db.session.add(new_chat)
        db.session.commit()
        return chat_schema.jsonify(new_chat), 201
    
    except Exception as e:
        print(f"Error creating chat: {e}")
        return jsonify({"message": "Internal Server Error"}), 500



# Delete a chat
@chat_bp.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        try:
            user_id = decode_token(token)
        except Exception as e:
            print(f"Error decoding token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        if not chat:
            return jsonify({"message": "Chat not found"}), 404

        if chat.user_id != user_id:
            return jsonify({"message": "Unauthorized"}), 403

        db.session.delete(chat)
        db.session.commit()

        return jsonify({"message": "Chat deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting chat: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

# Edit chat title
@chat_bp.route('/chats/<int:chat_id>', methods=['PUT'])
def update_chat_title(chat_id):
    try:
        data = request.json
        new_title = data.get('title')
        
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        try:
            user_id = decode_token(token)
        except Exception as e:
            print(f"Error decoding token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        if not new_title:
            return jsonify({"message": "Title is required"}), 400

        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"message": "Chat not found"}), 404

        if chat.user_id != user_id:
            return jsonify({"message": "Unauthorized"}), 403

        chat.title = new_title
        db.session.commit()

        return jsonify({"message": "Chat title updated successfully", "chat": chat_schema.dump(chat)}), 200
    except Exception as e:
        print(f"Error updating chat title: {e}")
        return jsonify({"message": "Internal Server Error"}), 500


# Endpoint to get all conversations for a chat
@chat_bp.route('/chats/<int:chat_id>/conversations', methods=['GET'])
def get_conversations(chat_id):
    try:
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        try:
            user_id = decode_token(token)
        except Exception as e:
            print(f"Error decoding token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        chat = Chat.query.get(chat_id)
        
        if not chat:
            return jsonify({"message": "Chat not found"}), 404

        if chat.user_id != user_id:
            return jsonify({"message": "Unauthorized"}), 403

        conversations = Conversation.query.filter_by(chat_id=chat_id).all()
        return jsonify(conversations_schema.dump(conversations)), 200
    except Exception as e:
        print(f"Error retrieving conversations: {e}")
        return jsonify({"message": "Internal Server Error"}), 500
    
# Get a certain conversation
@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    conversation = Conversation.query.get(conversation_id)
    
    token = extract_auth_token(request)
    if not token:
        return jsonify({"message": "Authentication token is required"}), 401
    
    try:
        user_id = decode_token(token)
    except Exception as e:
        print(f"Error decoding token: {e}")
        return jsonify({"message": "Invalid token"}), 401

    if not conversation:
        return jsonify({"message": "Conversation not found"}), 404

    chat = Chat.query.get(conversation.chat_id)
    if chat.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    return jsonify(conversation_schema.dump(conversation)), 200

# Endpoint to get all chats
@chat_bp.route('/chats', methods=['GET'])
def get_all_chats():
    try:
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        try:
            user_id = decode_token(token)
        except Exception as e:
            print(f"Error decoding token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        chats = Chat.query.filter_by(user_id=user_id).all()
        return chats_schema.jsonify(chats), 200
    except Exception as e:
        print(f"Error retrieving chats: {e}")
        return jsonify({"message": "Internal Server Error"}), 500



@chat_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    conversation_id = data.get('conversation_id')
    feedback_type = data.get('feedback_type', 'none')
    feedback_comment = data.get('feedback_comment', '')

    if not conversation_id or not feedback_type:
        return jsonify({"message": "conversation_id and feedback_type are required"}), 400

    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"message": "Conversation not found"}), 404

    feedback = Feedback(
        conversation_id=conversation_id,
        feedback_type=feedback_type,
        feedback_comment=feedback_comment
    )

    db.session.add(feedback)
    db.session.commit()

    if feedback_type == 'positive':
        user_id = conversation.chat.user_id  # Assuming you have a relationship to get the user_id
        user_collection_name = f"few_shot_user_{user_id}"
        user_collection = client_chroma.get_or_create_collection(name=user_collection_name, embedding_function=openai_ef)

        # Extract the fields from the conversation
        question = conversation.user_query
        score = conversation.score
        executable = conversation.executable
        answer = conversation.sql_query
        location = conversation.location
        chartname= conversation.chartname

        # Ensure all fields are available
        if question and answer and score is not None and executable and location and chartname:
            embedding = get_embeddings(question)
            
            # Generate a unique ID for the question
            unique_id = hashlib.md5(question.encode()).hexdigest()

            # Store in the user-specific collection
            user_collection.add(
                ids=[unique_id],
                embeddings=[embedding],
                metadatas=[{
                    "Question": question,
                    "Score": score,
                    "Executable": executable,
                    "Answer": answer,
                    "Location": location,
                    "ChartName": chartname
                }]
            )

    return jsonify({"message": "Feedback submitted successfully"}), 201

#Edit feedback
@chat_bp.route('/conversations/<int:conversation_id>/feedback', methods=['PUT'])
def update_feedback(conversation_id):
    try:
        data = request.json
        feedback_comment = data.get('feedback_comment', '')

        # Fetch the feedback associated with the conversation ID
        feedback = Feedback.query.filter_by(conversation_id=conversation_id).first()
        if not feedback:
            return jsonify({"message": "Feedback not found"}), 404

        # Check if the feedback is negative
        if feedback.feedback_type != 'negative':
            return jsonify({"message": "Cannot update feedback. Only negative feedback can be updated."}), 400

        feedback.feedback_comment = feedback_comment
        db.session.commit()

        return jsonify({"message": "Feedback updated successfully"}), 200
    except Exception as e:
        print(f"Error updating feedback: {e}")
        return jsonify({"message": "Internal Server Error"}), 500


#Get a certain feedback
@chat_bp.route('/conversations/<int:conversation_id>/feedback', methods=['GET'])
def get_feedback(conversation_id):
    try:
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        # Query feedback based on conversation_id and user_id
        feedback = Feedback.query.filter_by(conversation_id=conversation_id).all()

        if not feedback:
            return jsonify({'message': 'Feedback not found'}), 404

        # Serialize feedback using your schema
        serialized_feedback = feedbacks_schema.dump(feedback)

        return jsonify(serialized_feedback), 200

    except Exception as e:
        print(f"Error retrieving feedback: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

#Get all feedbacks
@chat_bp.route('/feedback', methods=['GET'])
def get_all_feedback():
    try:
        token = extract_auth_token(request)
        if not token:
            return jsonify({"message": "Authentication token is required"}), 401
        
        # Query all feedback entries in the database
        feedbacks = Feedback.query.all()

        if not feedbacks:
            return jsonify({'message': 'No feedback found'}), 404

        # Serialize the list of feedback entries using your schema
        serialized_feedbacks = feedbacks_schema.dump(feedbacks)

        return jsonify(serialized_feedbacks), 200

    except Exception as e:
        print(f"Error retrieving feedback: {e}")
        return jsonify({"message": "Internal Server Error"}), 500
    



#Main asking route
@chat_bp.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_question = data.get('question')
    chat_id = data.get('chat_id')

    if not user_question or not chat_id:
        return jsonify({"message": "Question and chat_id are required"}), 400

    # Check for sensitive information
    if contains_sensitive_info(user_question):
        return jsonify({"message": "This question asks for sensitive content and I am not allowed to answer it."}), 403

    # Fetch previous conversations for context
    previous_conversations = Conversation.query.filter_by(chat_id=chat_id).order_by(Conversation.timestamp).all()

    # Create the system message with all instructions and context
    conversation_history = [
        {
            "role": "system",
            "content": db_schema_prompt + """
                The user will be asking questions about a database with the schema described above. 
                The user does not have access to the column names in the database, so he may ask questions that do not contain the column name specifically; therefore, you must be able to deduce what he wants.
                Guidelines to fill out answer fields:
                1) Field Type: If the type of the field, which is given at the end of each field, is "string"; then, your answer for that field must be between double quotations.
                2) SQL command: The sentence written in the "Answer" field should be a valid SQL command that can be executed in PostgreSQL.
                3) Data Sensitivity: Do not generate SQL commands that retrieve sensitive information such as passwords, primary keys, IDs, or API keys. It is okay for the user to ask for directions to a certain location.
                4) Read-Only Operations: Do not generate SQL queries that involve data-altering operations such as DELETE or UPDATE.
                Your primary objective is to read each question and return 4 fields as JSON string as follows:
                {
                    "Score": On a scale of 1-10, how relevant is the user question or statement to the content of the database where 1 is the lowest and 10 is the highest. Be cautious that the user may be sending a follow-up question or statement that may appear irrelevant at first glance, but it could be relevant. Type: integer. Options: 1-10.
                    "Executable": An "Answer" is executable if it satisfies the above guidelines. If at least one of the guidelines fails then answer with "No" and write "NULL" in the "Answer" field. Type: string. Options: "Yes" or "No".                
                    "Answer": one or multiple SQL queries (if they are multiple then they should be separated by ;) to fetch the required information from the database without any additional text or explanation. The command(s) should be compatible with PostgreSQL. Always put identifiers in the SQL queries between double quotations. Type: string.
                    "Location": Does the user sentence or question ask about a location? Type: string. Options: "Yes" or "No". 
                    "ChartName": The type of visualization or map to be generated if any. The user may explicitly ask for the generation of a specific type of chart (e.g., 'LineChart', 'BarChart', 'PieChart') or a heatmap which is a representation of data points where individual values are depicted by varying colors, please note that heatmaps are not related to actual maps; therefore, they dont require any address ('HeatMap'). Additionally, the user might request directions to a certain location ('GoogleMaps') or the creation of a triangle/polygon map based on three input locations to visualize a specific area ('TriangleMaps'). If none of these are requested, reply with 'None'. Options: 'LineChart', 'BarChart', 'PieChart', 'GoogleMaps', 'HeatMap', 'TriangleMaps', 'None'. Type: string.
                }
                Important Notes:
                1) Contextual Understanding: Understand and maintain context as the user may ask follow-up questions. In some cases, follow-up questions or statements may be unclear at first. For example, the user could ask for addresses which are returned to him in a list, then he sends "2" in a follow-up message which means that he wants the second option. 
                2) Location-related information (such as address, city, state) and contact information are not considered sensitive and you may retrieve them. If the user asks a location related question then you must fetch the full address that answers that question. When you write queries that fetch state or city, the data may be stored as an abbreviation; example: "California" and "CA".
                3) HeatMaps: HeatMaps are not related in any way to actual location-based maps. Never fetch locations for a heatmap unless the user explicitly asks you to do so. When the user asks for heatmap, he will specify what data would be the x-axis, y-axis and data points. You must fetch what he wants in the following order: x-axis, y axis, data points.
            """
        }
    ]

    # Append previous conversations in alternating user and assistant roles
    for convo in previous_conversations:
        user_query_with_feedback = convo.user_query
        feedbacks = Feedback.query.filter_by(conversation_id=convo.id, feedback_type='negative').all()
        for feedback in feedbacks:
            user_query_with_feedback += f" (Negative feedback on assistant response: {feedback.feedback_comment})"
        conversation_history.append({"role": "user", "content": user_query_with_feedback})
        conversation_history.append({
            "role": "assistant",
            "content": json.dumps({
                "Score": convo.score,
                "Executable": convo.executable,
                "Answer": convo.sql_query,
                "Location": convo.location,
                "ChartName": convo.chartname
            })
        })

    # Add the current user question
    conversation_history.append({"role": "user", "content": user_question})
    # Get user_id from the chat
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({"message": "Chat not found"}), 404
    user_id = chat.user_id
    # Generate SQL query and extract relevant fields
    sql_query, score, executable, location, chartname = generate_sql_query(user_question, conversation_history, user_id)

    if score < 4:
        return jsonify({"message": "I'm here to answer questions related to the database. Could you please ask something relevant?"}), 403
    if executable == "No":
        return jsonify({"message": "This question asks for sensitive content and I am not allowed to answer it."}), 403

    
    # Check for data-altering operations
    if contains_data_altering_operations(sql_query):
        return jsonify({"message": "Data-altering operations are not allowed."}), 403

    try:
        engine = db.get_engine(current_app, bind='TestingData')
        session = engine.connect()
        data = session.execute(text(sql_query))
        result=data.fetchall()

        print(f"SQL Query Result: {result}")
        if chartname in ["LineChart", "BarChart", "PieChart"]:
            keys=data.keys()
            keys=list(keys)
            print(keys)
            if len(keys)>2:
                formatted_response = format_as_table(result,keys)
            else:
                result_adjusted = [{"labelX": str(row[0]), "labelY": row[1]} for row in result]
                chart_code = generate_chart_code(result_adjusted, keys[0], keys[1], chartname, chart_base_code)
                formatted_response = f"Here is your {chartname}: {chart_code}"
        elif chartname== "HeatMap":
            keys=data.keys()
            keys=list(keys)
            print(keys)
            if len(keys)>3:
                formatted_response = format_as_table(result,keys)
            else:
                xlabels = list(set([row[0] for row in result]))
                ylabels = list(set([row[1] for row in result]))
        
                # Initialize the heatmap data with zeros
                heatmap_data = [[0 for _ in xlabels] for _ in ylabels]
        
                # Populate the heatmap data with actual values
                for row in result:
                    x_index = xlabels.index(row[0])
                    y_index = ylabels.index(row[1])
                    heatmap_data[y_index][x_index] = row[2]
                print(heatmap_data)
                heat_code = generate_heatmap_code(xlabels, ylabels, heatmap_data, heat_base_code)
                formatted_response = f"Here is your heatmap: {heat_code}"

        elif len(result) > 30:
            keys=data.keys()
            keys=list(keys)
            formatted_response = format_as_table(result,keys)
        elif location == "Yes" and chartname =="GoogleMaps":
            if len(result) > 1:
                formatted_response = format_response_with_gpt(user_question, result, previous_conversations)
            else:
                address = format_address(result[0])
                lat , lng = get_google_maps_loc(address)
                coordinates=[{"lat":lat , "lng":lng }]
                map_code = generate_map_code(coordinates,chartname,map_base_code)
                formatted_response = f"Here is the map to {address}: {map_code}"
        elif location == "Yes" and chartname == "TriangleMaps":
            if len(result)==3:
                coordinates=[]
                for row in result:
                    address = format_address(row)
                    lat , lng =get_google_maps_loc(address)
                    coordinates.append({"lat":lat , "lng":lng})
                map_code=generate_map_code(coordinates,chartname,map_base_code)
                formatted_response = f"Here is your requested area: {map_code}"
            else:
                formatted_response = format_response_with_gpt(user_question, result, previous_conversations)
        else:
            formatted_response = format_response_with_gpt(user_question, result, previous_conversations)

       # Store the conversation
        conversation = Conversation(
            chat_id=chat_id,
            user_query=user_question,
            response=formatted_response,
            sql_query=sql_query,
            score=score,
            executable=executable,
            location=location,
            chartname=chartname
        )
        db.session.add(conversation)
        db.session.commit()

        return jsonify({"message": formatted_response}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"message": str(e)}), 500
    finally:
        session.close()




def generate_sql_query(user_question, conversation_history,user_id):
    relevant_examples = select_relevant_few_shots(user_question,user_id=user_id, top_n_main=5,top_n_user=2,distance_threshold=1.5)

    example_texts = "\n".join(
    [f"User Question: \"{ex['Question']}\"\n \"Score\": {ex['Score']}\n\"Executable\": \"{ex['Executable']}\"\n\"Answer\": \"{ex['Answer']}\"\n\"Location\": \"{ex['Location']}\"" for ex in relevant_examples]
    )

    # Append examples and instructions to the system message
    conversation_history[0]["content"] += f"\nThe following are examples of User questions and corresponding replies:\n{example_texts}"
    
    print(conversation_history)
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=conversation_history,
        max_tokens=700
    )
    gpt_response = response.choices[0].message.content.strip()
    print(gpt_response)

    try:
        response_json = json.loads(gpt_response)
        score = response_json["Score"]
        executable = response_json["Executable"]
        sql_query = response_json["Answer"]
        location = response_json["Location"]
        chartname = response_json["ChartName"]
    except json.JSONDecodeError:
        score = None
        executable = "No"
        sql_query = "NULL"
        location = "No"
        chartname = "None"



    # Replace MONTH and YEAR functions with EXTRACT for PostgreSQL compatibility
    if sql_query != "NULL":
        sql_query = sql_query.replace("MONTH(", "EXTRACT(MONTH FROM ")
        sql_query = sql_query.replace("YEAR(", "EXTRACT(YEAR FROM ")

    return sql_query, score, executable, location, chartname





def format_response_with_gpt(user_question, data, previous_conversations):
    message=[{"role":"system","content":
                '''
                Your goal is to format the final answer given by the user in a user-friendly way and a full brief sentence taking into consideration his feedback if he has any.
                There are 2 cases:
                Case 1:
                If there only one answer is given then format the final answer given by the user in a user-friendly way. And at the end, ask a kind question similar to "Is there anything else I can assist you with?", but change this question often in order to avoid repitition.
                Case 2:
                If multiple answers are given then you must format them in the following manner:
                *Brief introductory sentence*:
                *Numbered List with each element on a new line*
                1) ...
                2) ...
                3) ...
                *Appropriate question asking the user to choose*   
                '''
              }]
    for convo in previous_conversations:
        user_query_with_feedback = convo.user_query
        feedbacks = Feedback.query.filter_by(conversation_id=convo.id, feedback_type='negative').all()
        for feedback in feedbacks:
            user_query_with_feedback += f" (Negative feedback on assistant response: {feedback.feedback_comment})"
        message.append({"role": "user", "content": user_query_with_feedback})
        message.append({"role": "assistant", "content": convo.response})

        
    message.append({"role": "user", "content": f"{user_question}, Answer: {data}"})
    print(message)
    response = client.chat.completions.create(
        model='gpt-4o',  
        messages=message,
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()


