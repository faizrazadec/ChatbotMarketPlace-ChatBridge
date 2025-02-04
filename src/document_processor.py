# document_processor.py
import os
from uuid import uuid4
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain_unstructured import UnstructuredLoader
from dotenv import load_dotenv
from logger import setup_logger

logger = setup_logger()

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
        print(f"File: {file_path}")
        print("Number of LangChain pages:", len(pages))
        print("Length of text in the first page:", len(pages[0].page_content))
        return pages
    except Exception as e:
        print(f"Error loading document {file_path}: {e}")
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
def store_embeddings_in_chroma(pages, embeddings_list, collection_name, persist_directory):
    try:
        # Initialize Chroma vector store
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,  # Pass the embedding function to Chroma
            persist_directory=persist_directory,  # Where to save data locally
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
        print(f"Embeddings have been stored in Chroma collection: {collection_name}.")
    except Exception as e:
        print(f"Error storing embeddings in Chroma: {e}")

# Main function to process all files in a directory
def process_document(directory_path):
    # List all files in the directory
    if not os.path.isdir(directory_path):
        print(f"The provided path is not a valid directory: {directory_path}")
        return

    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
    if not files:
        print(f"No files found in the directory: {directory_path}")
        return

    # Process each file in the directory
    for file_name in files:
        file_path = os.path.join(directory_path, file_name)
        print(f"\nProcessing file: {file_path}")
        pages = load_document(file_path)
        if pages:
            embeddings_list = generate_embeddings(pages)
            if embeddings_list:
                # Create a unique collection name for each file
                collection_name = f"{os.path.splitext(file_name)[0]}_collection"
                logger.critical(f"Collection Name: {collection_name}")
                persist_directory = os.path.join(directory_path, "Chroma_db")
                store_embeddings_in_chroma(pages, embeddings_list, collection_name, persist_directory)
            else:
                print(f"Failed to generate embeddings for file: {file_name}")
        else:
            print(f"Failed to load the document: {file_name}")

# # Example usage
# if __name__ == "__main__":
#     directory_path = "user_docs/dataropes/7"  # Replace with your directory path
#     process_directory(directory_path)