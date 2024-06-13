import os
import pandas as pd
from extensions import db
from model.test import CustomerProfile, Product, PurchaseHistory
# Set environment variables
from dotenv import load_dotenv
load_dotenv()

# Ensure OPENAI_API_KEY is set
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

from app import app


#adjust paths as needed
def load_customer_profiles():
    df = pd.read_csv(r'C:\Users\Ihab\Downloads\customer_profile_dataset.csv')
    for index, row in df.iterrows():
        customer = CustomerProfile(
            customer_id=row['customer_id'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            gender=row['gender'],
            date_of_birth=pd.to_datetime(row['date_of_birth'], errors='coerce'),
            email=row['email'],
            phone_number=row['phone_number'],
            signup_date=pd.to_datetime(row['signup_date'], errors='coerce'),
            address=row['address'],
            city=row['city'],
            state=row['state'],
            zip_code=row['zip_code']
        )
        db.session.add(customer)
    db.session.commit()

def load_products():
    df = pd.read_csv(r'C:\Users\Ihab\Downloads\products_dataset.csv')
    for index, row in df.iterrows():
        product = Product(
            product_id=row['product_id'],
            product_name=row['product_name'],
            category=row['category'],
            price_per_unit=row['price_per_unit'],
            brand=row['brand'],
            product_description=row['product_description']
        )
        db.session.add(product)
    db.session.commit()

def load_purchase_history():
    df = pd.read_csv(r'C:\Users\Ihab\Downloads\purchase_history_dataset.csv')
    for index, row in df.iterrows():
        purchase = PurchaseHistory(
            purchase_id=row['purchase_id'],
            customer_id=row['customer_id'],
            product_id=row['product_id'],
            purchase_date=pd.to_datetime(row['purchase_date'], errors='coerce'),
            quantity=row['quantity'],
            total_amount=row['total_amount']
        )
        db.session.add(purchase)
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        load_customer_profiles()
        load_products()
        load_purchase_history()
