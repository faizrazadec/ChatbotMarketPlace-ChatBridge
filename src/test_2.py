import os
from uuid import uuid4
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain_unstructured import UnstructuredLoader
from dotenv import load_dotenv
import sqlite3  # Assuming you're using SQLite for the database
from datetime import datetime

# Load environment variables
load_dotenv()

# Load your API key for Google Generative AI Embeddings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Specify the file path for the document
file_path = "src/user_docs/dataropes/1/HowachatbotcansupporttheHRfunction.pdf"  # Replace with your document path

# Initialize the Google Embeddings model
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",  # Specify the embedding model
    google_api_key=GEMINI_API_KEY,
    task_type="retrieval_document",  # Adjust if necessary for your use case
)

# Function to retrieve the document path from the database
def get_document_paths(username, bot_id):
    conn = sqlite3.connect('users.db')  # Adjust the DB path if needed
    c = conn.cursor()

    try:
        # Fetch document paths from the database for the specific bot
        c.execute("SELECT documents FROM chatbots WHERE username = ? AND id = ?", (username, bot_id))
        result = c.fetchone()

        if result and result[0]:
            # Return the document paths as a list
            return result[0].split(',')
        else:
            return []
    except Exception as e:
        print(f"Error fetching document paths: {e}")
        return []
    finally:
        conn.close()

# Function to load the document and chunk it
def load_document(file_path, chunk_size=10000):
    try:
        # Initialize the UnstructuredLoader with lazy loading
        loader = UnstructuredLoader(
            file_path,
            chunking_strategy="basic",  # You can adjust chunking strategy here
            max_characters=chunk_size,
            include_orig_elements=False
        )

        # Lazy load the document and append pages to the pages list
        pages = []
        for doc in loader.lazy_load():  # Use lazy_load to process document pages
            pages.append(doc)

        # Print the number of pages and the length of text in the first page
        print("Number of LangChain pages:", len(pages))
        print("Length of text in the first page:", len(pages[0].page_content))

        return pages
    except Exception as e:
        print(f"Error loading document: {e}")
        return None

# Function to generate embeddings using Google Embeddings
def generate_embeddings(pages):
    try:
        # Extract text content for embedding generation
        page_texts = [page.page_content for page in pages]  # Use pages directly since chunking is already done

        # Generate embeddings for each page using Google Embeddings
        embeddings_list = embeddings.embed_documents(page_texts)

        # Print embeddings shape (for debugging)
        print(f"Embeddings shape: {len(embeddings_list)} embeddings generated")

        return embeddings_list
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

# Function to store embeddings in Chroma vector store
def store_embeddings_in_chroma(pages, embeddings_list):
    try:
        # Initialize Chroma vector store
        vector_store = Chroma(
            collection_name="HR_Collection",
            embedding_function=embeddings,  # Pass the embedding function to Chroma
            persist_directory="./Chroma_db",  # Where to save data locally
        )

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
        print(f"Error storing embeddings in Chroma: {e}")

# Main function to process the document
def process_document(file_path):
    pages = load_document(file_path)

    if pages:
        embeddings_list = generate_embeddings(pages)

        if embeddings_list:
            store_embeddings_in_chroma(pages, embeddings_list)
        else:
            print("Failed to generate embeddings.")
    else:
        print("Failed to load the document.")

# Example usage
if __name__ == "__main__":
    process_document(file_path)
