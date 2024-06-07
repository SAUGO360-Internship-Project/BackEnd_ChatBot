from extensions import db, ma, bcrypt

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    hashed_password = db.Column(db.String(255), nullable=False)

    
    def __init__(self, user_name, email, password):
        super(User, self).__init__(
        user_name = user_name,
        email = email)
        self.hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name", "email")
        model = User

user_schema = UserSchema()



