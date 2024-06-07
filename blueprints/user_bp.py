from flask import Blueprint, request, jsonify
from model.user import User, user_schema
from extensions import db, bcrypt

user_bp = Blueprint('user_bp', __name__)