from extensions import db, ma, bcrypt
from model.chat import Chat

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)
    secret_key = db.Column(db.String(128), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    bio_description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)  # This can be a URL or path to the image
    chats = db.relationship('Chat', backref='user', lazy=True, cascade='all, delete-orphan')

    def __init__(self, user_name, email, password, secret_key, phone_number=None, gender=None, bio_description=None, address=None, profile_image=None):
        super(User, self).__init__(
        user_name = user_name,
        email = email)
        self.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.secret_key = secret_key
        self.phone_number = phone_number 
        self.gender = gender
        self.bio_description= bio_description
        self.address = address
        self.profile_image = profile_image

class UserSchema(ma.Schema): 
    class Meta:
        fields = ("id", "user_name", "email", "phone_number", "gender", "bio_description", "address", "profile_image")
        model = User

user_schema = UserSchema()
