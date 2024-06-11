from flask import Blueprint, request, jsonify
from model.few_shot import FewShot, few_shot_schema, few_shot_schemas
from extensions import db

fewshot_bp = Blueprint('fewshot_bp', __name__)

@fewshot_bp.route('/fewshot', methods=['POST'])
def add_few_shot():
    data = request.json
    question = data.get('question')
    sql_query = data.get('sql_query')

    if not question or not sql_query:
        return jsonify({"error": "Question and SQL query are required"}), 400

    few_shot = FewShot(question=question, sql_query=sql_query)
    db.session.add(few_shot)
    db.session.commit()

    return jsonify(few_shot_schema.dump(few_shot)), 201

@fewshot_bp.route('/fewshot', methods=['GET'])
def get_few_shots():
    few_shots = FewShot.query.all()
    return jsonify(few_shot_schemas.dump(few_shots))

@fewshot_bp.route('/fewshot/<int:id>', methods=['DELETE'])
def delete_few_shot(id):
    few_shot = FewShot.query.get(id)
    if not few_shot:
        return jsonify({"error": "Example not found"}), 404

    db.session.delete(few_shot)
    db.session.commit()
    return '', 204
