from extensions import db, ma, bcrypt
from model.chat import Chat

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')
    secret_key = db.Column(db.String(128), nullable=False)

    
    def __init__(self, user_name, email, password, secret_key):
        super(User, self).__init__(
        user_name = user_name,
        email = email)
        self.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.secret_key = secret_key


class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name", "email", "qr_code_url")
        model = User

user_schema = UserSchema()



