# embedding_generator.py

import os
from uuid import uuid4
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load your API key for Google Generative AI Embeddings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize the Google Embeddings model
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",  # Specify the embedding model
    google_api_key=GEMINI_API_KEY,
    task_type="retrieval_document",  # Adjust if necessary for your use case
)

# Function to generate embeddings and store them in Chroma
def generate_embeddings_and_store(pages, vector_store, chunk_size=10000):
    try:
        # Extract text content for embedding generation
        page_texts = [page.page_content for page in pages]  # Use pages directly since chunking is already done

        # Generate embeddings for each page using Google Embeddings
        embeddings_list = embeddings.embed_documents(page_texts)

        # Generate unique IDs for the documents
        uuids = [str(uuid4()) for _ in range(len(pages))]

        # Prepare the documents as langchain Document objects
        documents = [
            Document(page_content=page.page_content) for page in pages
        ]

        # Add each embedding to the Chroma collection using add_documents method
        vector_store.add_documents(
            documents=documents, embeddings=embeddings_list, ids=uuids
        )

        print("Embeddings have been stored in Chroma.")
    except Exception as e:
        print(f"Error generating and storing embeddings: {e}")
