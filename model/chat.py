from extensions import db, ma
from datetime import datetime


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    feedback_type = db.Column(db.String(10), nullable=False, default='none')  # 'positive', 'negative', or 'none'
    feedback_comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, conversation_id, feedback_type='none', feedback_comment=None):
        self.conversation_id = conversation_id
        self.feedback_type = feedback_type
        self.feedback_comment = feedback_comment


class FeedbackSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Feedback
        fields = ("id", "conversation_id", "feedback_type", "feedback_comment", "timestamp")


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    user_query = db.Column(db.String(500), nullable=False)
    response = db.Column(db.String(2000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    feedbacks = db.relationship('Feedback', backref='conversation', lazy=True)

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
feedback_schema = FeedbackSchema()

# Plural schema instances
chats_schema = ChatSchema(many=True)
conversations_schema = ConversationSchema(many=True)
feedbacks_schema = FeedbackSchema(many=True)
