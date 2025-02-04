# document_processor.py
import os
from uuid import uuid4
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain_unstructured import UnstructuredLoader
from dotenv import load_dotenv
import sqlite3

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GEMINI_API_KEY,
    task_type="retrieval_document",
)

def get_document_paths(username, bot_id):
    conn = sqlite3.connect('src/users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT documents FROM chatbots WHERE username = ? AND id = ?", (username, bot_id))
        result = c.fetchone()
        if result and result[0]:
            return result[0].split(',')
        else:
            return []
    except Exception as e:
        print(f"Error fetching document paths: {e}")
        return []
    finally:
        conn.close()

def load_document(file_path, chunk_size=10000):
    try:
        loader = UnstructuredLoader(
            file_path,
            chunking_strategy="basic",
            max_characters=chunk_size,
            include_orig_elements=False
        )
        pages = [doc for doc in loader.lazy_load()]
        print("Number of LangChain pages:", len(pages))
        print("Length of text in the first page:", len(pages[0].page_content))
        return pages
    except Exception as e:
        print(f"Error loading document: {e}")
        return None

def generate_embeddings(pages):
    try:
        page_texts = [page.page_content for page in pages]
        embeddings_list = embeddings.embed_documents(page_texts)
        print(f"Embeddings generated for {len(embeddings_list)} pages")
        return embeddings_list
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

def store_embeddings_in_chroma(username, bot_id, pages, embeddings_list):
    try:
        persist_directory = os.path.join('user_docs', username, str(bot_id))
        vector_store = Chroma(
            collection_name=f"bot_{bot_id}_collection",
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )
        uuids = [str(uuid4()) for _ in range(len(pages))]
        documents = [Document(page_content=page.page_content) for page in pages]
        vector_store.add_documents(documents=documents, embeddings=embeddings_list, ids=uuids)
        vector_store.persist()
        print(f"Embeddings stored in Chroma for bot {bot_id}.")
    except Exception as e:
        print(f"Error storing embeddings in Chroma: {e}")

def process_document(username, bot_id):
    document_paths = get_document_paths(username, bot_id)
    if document_paths:
        for file_path in document_paths:
            full_file_path = os.path.join('user_docs', username, str(bot_id), file_path)
            if os.path.exists(full_file_path):
                print(f"Processing document: {full_file_path}")
                pages = load_document(full_file_path)
                if pages:
                    embeddings_list = generate_embeddings(pages)
                    if embeddings_list:
                        store_embeddings_in_chroma(username, bot_id, pages, embeddings_list)
                    else:
                        print("Failed to generate embeddings.")
                else:
                    print(f"Failed to load the document: {file_path}")
            else:
                print(f"Document file not found: {full_file_path}")
    else:
        print("No documents found for the specified bot.")

if __name__ == "__main__":
    process_document(username="test_user", bot_id=1)
