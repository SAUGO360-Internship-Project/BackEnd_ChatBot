# from flask import Blueprint, request, jsonify
# from model.few_shot import FewShot, few_shot_schema, few_shot_schemas
# from extensions import db

# fewshot_bp = Blueprint('fewshot_bp', __name__)

# @fewshot_bp.route('/fewshot', methods=['POST'])
# def add_few_shot():
#     data = request.json
#     question = data.get('question')
#     sql_query = data.get('sql_query')

#     if not question or not sql_query:
#         return jsonify({"error": "Question and SQL query are required"}), 400

#     few_shot = FewShot(question=question, sql_query=sql_query)
#     db.session.add(few_shot)
#     db.session.commit()

#     return jsonify(few_shot_schema.dump(few_shot)), 201

# @fewshot_bp.route('/fewshot', methods=['GET'])
# def get_few_shots():
#     few_shots = FewShot.query.all()
#     return jsonify(few_shot_schemas.dump(few_shots))

# @fewshot_bp.route('/fewshot/<int:id>', methods=['DELETE'])
# def delete_few_shot(id):
#     few_shot = FewShot.query.get(id)
#     if not few_shot:
#         return jsonify({"error": "Example not found"}), 404

#     db.session.delete(few_shot)
#     db.session.commit()
#     return '', 204



from flask import Blueprint, request, jsonify
import chromadb
import numpy as np
from openai import OpenAI
import os
from extensions import get_embeddings

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize Chroma client and connect to the collection
chroma_client = chromadb.Client()
collection_name = "few_shot"
collection = chroma_client.get_collection(name=collection_name)


fewshot_bp = Blueprint('fewshot_bp', __name__)

@fewshot_bp.route('/fewshot', methods=['POST'])
def add_few_shot():
    data = request.json
    question = data.get('question')
    sql_query = data.get('sql_query')

    if not question or not sql_query:
        return jsonify({"error": "Question and SQL query are required"}), 400

    embedding = get_embeddings(question)
    collection.add(
        ids=str(question),  # You can use a unique identifier here if needed
        embeddings=[embedding],
        metadatas=[{"question": question, "sql_query": sql_query}]
    )

    return jsonify({"message": "Few-shot example added successfully"}), 201

@fewshot_bp.route('/fewshot', methods=['GET'])
def get_few_shots():
    results = collection.query(embeddings=[], top_k=5, include_metadatas=True)  # Adjust top_k as needed
    few_shots = [{"id": result["id"], "question": result["metadata"]["question"], "sql_query": result["metadata"]["sql_query"]} for result in results["matches"]]
    return jsonify(few_shots),200

@fewshot_bp.route('/fewshot/<string:question>', methods=['DELETE'])
def delete_few_shot(question):
    collection.delete(ids=[question])
    return '', 204

