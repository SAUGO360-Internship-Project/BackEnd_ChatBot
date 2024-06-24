import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions
import os

# Initialize ChromaDB client with a persistent local path
client = chromadb.PersistentClient(path="chroma_data", settings=Settings())

# Collection name
collection_name = "few_shot"
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=str(os.getenv('OPENAI_API_KEY')),
                model_name="text-embedding-3-large"
            )
# collection= client.create_collection(name=collection_name,embedding_function=openai_ef)
print(client.get_collection(name=collection_name,embedding_function=openai_ef))

