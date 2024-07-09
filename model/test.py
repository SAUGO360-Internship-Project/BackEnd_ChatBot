from extensions import db, ma

class Consumer(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'consumers'
    Consumer_ID = db.Column(db.String(100), primary_key=True)
    City = db.Column(db.String(100), nullable=True)
    State = db.Column(db.String(100), nullable=True)
    Country = db.Column(db.String(100), nullable=True)
    Latitude = db.Column(db.Float, nullable=True)
    Longitude = db.Column(db.Float, nullable=True)
    Smoker = db.Column(db.String(50), nullable=True)
    Drink_Level = db.Column(db.String(50), nullable=True)
    Transportation_Method = db.Column(db.String(100), nullable=True)
    Marital_Status = db.Column(db.String(100), nullable=True)
    Children = db.Column(db.String(100), nullable=True)
    Age = db.Column(db.Integer, nullable=True)
    Occupation = db.Column(db.String(100), nullable=True)
    Budget = db.Column(db.String(100), nullable=True)

class ConsumerPreference(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'consumer_preferences'
    Consumer_ID = db.Column(db.String(100), db.ForeignKey('consumers.Consumer_ID'), primary_key=True)
    Preferred_Cuisine = db.Column(db.String(100), primary_key=True)
    consumer = db.relationship('Consumer', backref=db.backref('preferences', lazy=True))

class Rating(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'ratings'
    Consumer_ID = db.Column(db.String(100), db.ForeignKey('consumers.Consumer_ID'), primary_key=True)
    Restaurant_ID = db.Column(db.Integer, db.ForeignKey('restaurants.Restaurant_ID'), primary_key=True)
    Overall_Rating = db.Column(db.Integer, nullable=True)
    Food_Rating = db.Column(db.Integer, nullable=True)
    Service_Rating = db.Column(db.Integer, nullable=True)
    consumer = db.relationship('Consumer', backref=db.backref('ratings', lazy=True))
    restaurant = db.relationship('Restaurant', backref=db.backref('ratings', lazy=True))

class Restaurant(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'restaurants'
    Restaurant_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=True)
    City = db.Column(db.String(100), nullable=True)
    State = db.Column(db.String(100), nullable=True)
    Country = db.Column(db.String(100), nullable=True)
    Zip_Code = db.Column(db.String(20), nullable=True)
    Latitude = db.Column(db.Float, nullable=True)
    Longitude = db.Column(db.Float, nullable=True)
    Alcohol_Service = db.Column(db.String(50), nullable=True)
    Smoking_Allowed = db.Column(db.String(50), nullable=True)
    Price = db.Column(db.String(50), nullable=True)
    Franchise = db.Column(db.String(50), nullable=True)
    Area = db.Column(db.String(100), nullable=True)
    Parking = db.Column(db.String(100), nullable=True)

class RestaurantCuisine(db.Model):
    __bind_key__ = 'TestingData'
    __tablename__ = 'restaurant_cuisines'
    Restaurant_ID = db.Column(db.Integer, db.ForeignKey('restaurants.Restaurant_ID'), primary_key=True)
    Cuisine = db.Column(db.String(100), primary_key=True)
    restaurant = db.relationship('Restaurant', backref=db.backref('cuisines', lazy=True))
