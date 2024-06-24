from flask import Blueprint, request, jsonify
import chromadb
from chromadb.config import Settings
from extensions import get_embeddings
import hashlib
import chromadb.utils.embedding_functions as embedding_functions
import os

fewshot_bp = Blueprint('fewshot_bp', __name__)

# Initialize ChromaDB client with a persistent local path
client = chromadb.PersistentClient(path="chroma_data", settings=Settings())

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=str(os.getenv('OPENAI_API_KEY')),
                model_name="text-embedding-3-large"
            )
# Get or create the collection
collection_name = "few_shot"
collection = client.get_collection(name=collection_name,embedding_function=openai_ef)


@fewshot_bp.route('/fewshot', methods=['POST'])
def add_few_shot():
    data = request.json
    question = data.get('question')
    sql_query = data.get('sql_query')

    if not question or not sql_query:
        return jsonify({"error": "Question and SQL query are required"}), 400

    embedding = get_embeddings(question)
    
    # Generate a unique ID for the question
    unique_id = hashlib.md5(question.encode()).hexdigest()

    collection.add(
        ids=[unique_id],  # Use the unique ID as the identifier
        embeddings=[embedding],
        metadatas=[{"question": question, "sql_query": sql_query}]
    )
    return jsonify({"message": "Few-shot example added successfully.", "id": unique_id}), 201

@fewshot_bp.route('/fewshot', methods=['GET'])
def get_few_shots():
    limit = 3
    few_shots = []
    result = collection.get(limit=limit, include=["metadatas"])
    
    total_results = len(result['ids'])  # Get the actual number of results

    for x in range(total_results):  # Loop through the actual number of results
        few_shots.append({
            "id": result['ids'][x],
            "question": result['metadatas'][x]['question'],
            "sql_query": result['metadatas'][x]['sql_query']
        })
    return jsonify(few_shots), 200


@fewshot_bp.route('/fewshot/<string:id>', methods=['DELETE'])
def delete_few_shot(id):
    try:
        collection.delete(ids=[id])
        return jsonify({"message": "Few-shot example deleted successfully."}), 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500

