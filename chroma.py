# import chromadb
# import numpy as np
# from openai import OpenAI
# from dotenv import load_dotenv
# import os

# # Load environment variables from .env file
# load_dotenv()

# # Initialize OpenAI
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# # Initialize Chroma client and connect to the collection
# chroma_client = chromadb.Client()
# collection_name = "few_shot"
# collection = chroma_client.get_collection(name=collection_name)

# # Function to get embeddings
# def get_embeddings(text):
#     response = client.embeddings.create(
#         model="text-embedding-3-small",
#         input=text,
#         encoding_format="float"
#     )
#     return response.data[0].embedding 

# # Fetch few-shot examples from your database
# # For demonstration, we'll use a list of dictionaries
# few_shot_examples = [
#     {"id": 1, "question": "How many people are called Robert?", "sql_query": "SELECT COUNT(*) FROM customer_profile WHERE first_name = 'Robert';"},
#     {"id": 2, "question": "How many people are called Emma?", "sql_query": "SELECT COUNT(*) FROM customer_profile WHERE first_name = 'Emma';"}
#     # Add more examples as needed
# ]

# # Compute and store embeddings
# for example in few_shot_examples:
#     embedding = get_embeddings(example["question"])
#     # Store in Chroma collection
#     collection.add(
#         ids=str(example["id"]),
#         embeddings=[embedding],
#         metadatas=[{"question": example["question"], "sql_query": example["sql_query"]}]
#     )

# print("Embeddings stored successfully.")



import chromadb

# # Initialize Chroma client
client = chromadb.Client()

# Create a collection for storing few-shot examples
# collection_name = "few_shot"
# collection = client.create_collection(name=collection_name)

# print(f"Collection '{collection_name}' created successfully.")

collections = client.list_collections()
for col in collections:
    print(col.name)
