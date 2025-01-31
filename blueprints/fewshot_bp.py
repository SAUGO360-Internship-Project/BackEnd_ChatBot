from flask import Blueprint, request, jsonify
import chromadb
from chromadb.config import Settings
from extensions import get_embeddings
import hashlib
import chromadb.utils.embedding_functions as embedding_functions
import os

fewshot_bp = Blueprint('fewshot_bp', __name__)

client = chromadb.PersistentClient(path="chroma_data", settings=Settings())

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=str(os.getenv('OPENAI_API_KEY')),
                model_name="text-embedding-3-large"
            )

collection_name = "few_shot"
collection = client.get_or_create_collection(name=collection_name,embedding_function=openai_ef)


@fewshot_bp.route('/fewshot', methods=['POST'])
def add_few_shot():
    data = request.json
    question = data.get('Question')
    score = data.get('Score')
    executable = data.get('Executable')
    answer = data.get('Answer')
    location = data.get('Location')
    chartname=data.get('ChartName')


    if not question or not answer or not score or not executable or not location or not chartname:
        return jsonify({"error": "All fields are required"}), 400

    embedding = get_embeddings(question)
    
    # Generate a unique ID for the question
    unique_id = hashlib.md5(question.encode()).hexdigest()

    collection.add(
        ids=[unique_id],  # Use the unique ID as the identifier
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
            "Question": result['metadatas'][x]['Question'],
            "Score": result['metadatas'][x]['Score'],
            "Executable": result['metadatas'][x]['Executable'],
            "Answer": result['metadatas'][x]['Answer'],
            "Location": result['metadatas'][x]['Location'],
            "ChartName": result['metadatas'][x]['ChartName']

        })
    return jsonify(few_shots), 200



@fewshot_bp.route('/fewshot/<string:id>', methods=['DELETE'])
def delete_few_shot(id):
    try:
        collection.delete(ids=[id])
        return jsonify({"message": "Few-shot example deleted successfully."}), 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@fewshot_bp.route('/fewshot/all', methods=['DELETE'])
def delete_all_few_shots():
    try:
        result = collection.get(include=["metadatas"])
        all_ids = []
        for id in result['ids']:
            all_ids.append(id)
                
        collection.delete(ids=all_ids)
        return jsonify({"message": "All few-shot examples deleted successfully."}), 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500


