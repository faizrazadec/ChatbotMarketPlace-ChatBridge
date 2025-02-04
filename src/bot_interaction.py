import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_redis import RedisChatMessageHistory
from langchain_chroma import Chroma
from langchain.schema import Document
from logger import setup_logger

load_dotenv()
logger = setup_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
logger.info(f"Connecting to Redis at: {REDIS_URL}")

gemini_api_key = os.getenv('GEMINI_API_KEY')
llm = ChatGoogleGenerativeAI(
    model='gemini-1.5-flash',
    api_key=gemini_api_key
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    task_type="retrieval_document",
)

def get_relevant_documents_from_chroma(user_input: str, bot_id: int, username: str):
    try:
        directory_path = os.path.join("user_docs", username, str(bot_id))
        if not os.path.isdir(directory_path):
            logger.warning(f"Invalid directory: {directory_path}")
            return [], username

        files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        if not files:
            logger.warning(f"No files found in: {directory_path}")
            return [], username

        persist_directory = os.path.join(directory_path, "Chroma_db")
        if not os.path.exists(persist_directory):
            logger.warning(f"Chroma directory missing: {persist_directory}")
            return [], username

        relevant_documents = []

        for file_name in files:
            collection_name = os.path.splitext(file_name)[0]
            try:
                vector_store = Chroma(
                    collection_name=collection_name,
                    persist_directory=persist_directory,
                    embedding_function=embeddings,
                )
                logger.info(f"Processing collection: {vector_store._collection.name}")

                query_embedding = embeddings.embed_query(user_input)
                results = vector_store.similarity_search_by_vector(query_embedding, k=3)
                relevant_documents.extend([doc.page_content for doc in results])

            except Exception as e:
                logger.error(f"Error processing {collection_name}: {e}")

        return relevant_documents, username

    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return [], username

def build_system_prompt(company_name: str, domain: str, industry: str, bot_behavior: str) -> str:
    return f"""**Company Identity**
    You are an AI representative of {company_name}, operating in the {industry} industry with a focus on {domain}. 

    **Core Behavior Guidelines**
    1. Adhere strictly to this persona: {bot_behavior}
    2. Maintain professional communication aligned with {industry} standards
    3. Specialize in {domain}-related knowledge while acknowledging other areas
    4. Adapt tone to match user's communication style while staying professional
    5. If unsure about information, offer to follow up rather than speculate

    **Interaction Protocol**
    - Begin interactions with: "Welcome to {company_name}! How can I assist you today?"
    - Format responses using clear, concise paragraphs with industry-appropriate terminology
    - Escalate complex requests through proper channels when necessary
    - Maintain {industry}-compliant confidentiality standards

    **Domain-Specific Adaptation**
    Incorporate common {industry} practices and {domain} operational knowledge naturally into responses without explicit mention.

    **Boundary Clause**
    If asked about topics outside {domain} or {industry}, respond: "I specialize in {domain} for {company_name}. For other inquiries, please visit our website or contact support."
    """

def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(session_id, redis_url=REDIS_URL)

def get_bot_response(
    company_name: str,
    domain: str,
    industry: str,
    bot_behavior: str,
    user_input: str,
    session_id: str,
    bot_id: int,
    username: str  # Added username parameter
) -> str:
    try:
        logger.info(f"Processing request for {username} (bot {bot_id})")

        relevant_documents, username = get_relevant_documents_from_chroma(user_input, bot_id, username)
        context = "\n".join(relevant_documents) if relevant_documents else "No additional context available"

        system_prompt = build_system_prompt(company_name, domain, industry, bot_behavior)
        system_prompt += f"\n\nRelevant Context:\n{context}"

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        chain = prompt | llm | StrOutputParser()

        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_redis_history,
            input_messages_key="input",
            history_messages_key="history"
        )

        result = chain_with_history.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
        )

        logger.info(f"Successfully generated response for {username}")
        return result

    except Exception as e:
        logger.error(f"Error in get_bot_response: {str(e)}")
        return "Apologies, I'm experiencing technical difficulties. Please try again later."