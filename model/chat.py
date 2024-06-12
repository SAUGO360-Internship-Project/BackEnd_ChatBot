from extensions import db, ma
from datetime import datetime

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    user_query = db.Column(db.String(500), nullable=False)
    response = db.Column(db.String(2000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, chat_id, user_query, response):
        self.chat_id = chat_id
        self.user_query = user_query
        self.response = response

class ConversationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Conversation
        fields = ("id", "chat_id", "user_query", "response", "timestamp")

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    conversations = db.relationship('Conversation', backref='chat', lazy=True)

    def __init__(self, title):
        self.title = title

class ChatSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Chat
        fields = ("id", "title", "created_at")

# Single schema instances
chat_schema = ChatSchema()
conversation_schema = ConversationSchema()

# Plural schema instances
chats_schema = ChatSchema(many=True)
conversations_schema = ConversationSchema(many=True)
