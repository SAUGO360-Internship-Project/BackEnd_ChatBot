import numpy as np
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_embeddings(text):
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding 

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def select_relevant_few_shots(user_question, few_shot_examples, top_n=3):
    user_embedding = get_embeddings(user_question)
    similarities = []

    for example in few_shot_examples:
        example_embedding = get_embeddings(example.question)
        similarity = cosine_similarity(user_embedding, example_embedding)
        similarities.append((example, similarity))

    # Sort examples by similarity and select top_n
    similarities.sort(key=lambda x: x[1], reverse=True)
    relevant_examples = [ex[0] for ex in similarities[:top_n]]
    return relevant_examples
