import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions
import os

# Initialize ChromaDB client with a persistent local path
client = chromadb.PersistentClient(path="chroma_data", settings=Settings())

# Collection name
# collection_name = "few_shot"
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=str(os.getenv('OPENAI_API_KEY')),
                model_name="text-embedding-3-large"
            )
#collection= client.create_collection(name=collection_name,embedding_function=openai_ef)
# print(client.get_collection(name=collection_name,embedding_function=openai_ef))
# Initialize user-specific ChromaDB collection
# collection_name_user = "few_shot_users"
# collection_user = client.delete_collection(name=collection_name_user)
# print(client.get_collection(name=collection_name,embedding_function=openai_ef))
# print(client.list_collections())
# Get the list of collections
# client.delete_collection("user_1_pdfs")
collections = client.list_collections()

# Print the names of the collections
for collection in collections:
    print(collection.name)

