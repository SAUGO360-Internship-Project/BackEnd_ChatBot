import os
import pandas as pd
from extensions import db
from model.test import Consumer, ConsumerPreference, Rating, Restaurant, RestaurantCuisine
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()


# Ensure OPENAI_API_KEY is set
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

from app import app

def load_consumers():
    df = pd.read_csv(r"C:\Users\Saad\Desktop\consumers.csv")
    for index, row in df.iterrows():
        consumer = Consumer(
            Consumer_ID=row['Consumer_ID'],
            City=row['City'],
            State=row['State'],
            Country=row['Country'],
            Latitude=row['Latitude'],
            Longitude=row['Longitude'],
            Smoker=row['Smoker'],
            Drink_Level=row['Drink_Level'],
            Transportation_Method=row['Transportation_Method'],
            Marital_Status=row['Marital_Status'],
            Children=row['Children'],
            Age=row['Age'],
            Occupation=row['Occupation'],
            Budget=row['Budget']
        )
        db.session.add(consumer)
    db.session.commit()

def load_consumer_preferences():
    df = pd.read_csv(r"C:\Users\Saad\Desktop\consumer_preferences.csv")
    for index, row in df.iterrows():
        preference = ConsumerPreference(
            Consumer_ID=row['Consumer_ID'],
            Preferred_Cuisine=row['Preferred_Cuisine']
        )
        db.session.add(preference)
    db.session.commit()

def load_ratings():
    df = pd.read_csv(r"C:\Users\Saad\Desktop\ratings.csv")
    for index, row in df.iterrows():
        rating = Rating(
            Consumer_ID=row['Consumer_ID'],
            Restaurant_ID=row['Restaurant_ID'],
            Overall_Rating=row['Overall_Rating'],
            Food_Rating=row['Food_Rating'],
            Service_Rating=row['Service_Rating']
        )
        db.session.add(rating)
    db.session.commit()

def load_restaurants():
    df = pd.read_csv(r"C:\Users\Saad\Desktop\restaurants.csv")
    for index, row in df.iterrows():
        restaurant = Restaurant(
            Restaurant_ID=row['Restaurant_ID'],
            Name=row['Name'],
            City=row['City'],
            State=row['State'],
            Country=row['Country'],
            Zip_Code=row['Zip_Code'],
            Latitude=row['Latitude'],
            Longitude=row['Longitude'],
            Alcohol_Service=row['Alcohol_Service'],
            Smoking_Allowed=row['Smoking_Allowed'],
            Price=row['Price'],
            Franchise=row['Franchise'],
            Area=row['Area'],
            Parking=row['Parking']
        )
        db.session.add(restaurant)
    db.session.commit()

def load_restaurant_cuisines():
    df = pd.read_csv(r"C:\Users\Saad\Desktop\restaurant_cuisines.csv")
    for index, row in df.iterrows():
        cuisine = RestaurantCuisine(
            Restaurant_ID=row['Restaurant_ID'],
            Cuisine=row['Cuisine']
        )
        db.session.add(cuisine)
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        load_consumers()
        load_consumer_preferences()
        load_restaurants()
        load_ratings()
        load_restaurant_cuisines()
