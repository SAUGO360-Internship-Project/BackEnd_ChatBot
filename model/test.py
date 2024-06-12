from extensions import db, ma

class CustomerProfile(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'customer_profile'
    customer_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    email = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    signup_date = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)

class Product(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    price_per_unit = db.Column(db.Float, nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    product_description = db.Column(db.Text, nullable=True)

class PurchaseHistory(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'purchase_history'
    purchase_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_profile.customer_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

    customer = db.relationship('CustomerProfile', backref=db.backref('purchases', lazy=True))
    product = db.relationship('Product', backref=db.backref('purchases', lazy=True))
