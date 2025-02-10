"""
Bot Interaction Module
Handles bot response generation with LangChain, Google Gemini, Redis, and Chroma.
"""

from langchain.callbacks.tracers import LangChainTracer
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_redis import RedisChatMessageHistory
from langchain_chroma import Chroma
from logger import setup_logger

# Load environment variables first
load_dotenv()
logger = setup_logger()

langsmith_tracer = LangChainTracer()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
logger.info("Connecting to Redis at: %s", REDIS_URL)

gemini_api_key = os.getenv("GEMINI_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=gemini_api_key)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    task_type="retrieval_document",
)


def get_relevant_documents_from_chroma(user_input: str, bot_name: str, username: str):
    """
    Retrieves the most relevant documents from the user's Chroma database based on input.

    Args:
        user_input (str): The query provided by the user.
        bot_name (str): The chatbot's name.
        username (str): The user's identifier.

    Returns:
        tuple: A list of relevant documents and the username.
    """
    try:
        directory_path = os.path.join("user_docs", username, str(bot_name))
        if not os.path.isdir(directory_path):
            logger.warning("Invalid directory: %s", directory_path)
            return [], username

        files = [
            f
            for f in os.listdir(directory_path)
            if os.path.isfile(os.path.join(directory_path, f))
        ]
        if not files:
            logger.warning("No files found in: %s", directory_path)
            return [], username

        persist_directory = os.path.join(directory_path, "Chroma_db")
        if not os.path.exists(persist_directory):
            logger.warning("Chroma directory missing: %s", persist_directory)
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
                logger.info("Processing collection: %s", vector_store._collection.name)

                query_embedding = embeddings.embed_query(user_input)
                results = vector_store.similarity_search_by_vector(query_embedding, k=3)
                relevant_documents.extend([doc.page_content for doc in results])

            except Exception as e:
                logger.error("Error processing %s: %s", collection_name, e)

        return relevant_documents, username

    except Exception as e:
        logger.error("Error retrieving documents: %s", e)
        return [], username


def build_system_prompt(
    bot_name: str, company_name: str, domain: str, industry: str, bot_behavior: str
) -> str:
    """
    Constructs the system prompt defining the bot's behavior and domain.

    Args:
        bot_name (str): Chatbot's name.
        company_name (str): Associated company.
        domain (str): Knowledge domain.
        industry (str): Business industry.
        bot_behavior (str): AI behavior and persona.

    Returns:
        str: Formatted system prompt.
    """
    return f"""**Company Identity**
    Your name is {bot_name} and You are an AI representative of {company_name},
    operating in the {industry} industry with a focus on {domain}.

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
    Incorporate common {industry} practices and {domain} operational
    knowledge naturally into responses without explicit mention.

    **Boundary Clause**
    If asked about topics outside {domain} or {industry}, respond: "I specialize
    in {domain} for {company_name}. For other inquiries, please visit our website or contact support."
    """


def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    """
    Retrieves chat history from Redis.

    Args:
        session_id (str): Unique session identifier.

    Returns:
        RedisChatMessageHistory: Chat history object.
    """
    return RedisChatMessageHistory(session_id, redis_url=REDIS_URL)


def get_bot_response(
    bot_name: str,
    company_name: str,
    domain: str,
    industry: str,
    bot_behavior: str,
    user_input: str,
    session_id: str,
    bot_id: int,
    username: str,
) -> str:
    """
    Generates a chatbot response based on user input and context.

    Args:
        bot_name (str): Chatbot's name.
        company_name (str): Associated company.
        domain (str): Bot's knowledge domain.
        industry (str): Business industry.
        bot_behavior (str): AI behavior and persona.
        user_input (str): User's input query.
        session_id (str): Unique session identifier.
        bot_id (int): Chatbot's ID.
        username (str): User's identifier.

    Returns:
        str: Chatbot response.
    """
    try:
        logger.info("Processing request for %s (bot %s)", username, bot_id)

        relevant_documents, username = get_relevant_documents_from_chroma(
            user_input, bot_name, username
        )
        context = (
            "\n".join(relevant_documents)
            if relevant_documents
            else "No additional context available"
        )

        system_prompt = build_system_prompt(
            bot_name, company_name, domain, industry, bot_behavior
        )
        system_prompt += f"\n\nRelevant Context:\n{context}"

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template("{input}"),
            ]
        )

        chain = prompt | llm | StrOutputParser()

        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_redis_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        result = chain_with_history.invoke(
            {"input": user_input}, config={"configurable": {"session_id": session_id}}
        )

        logger.info("Successfully generated response for %s", username)
        return result

    except Exception as e:
        logger.error("Error in get_bot_response: %s", str(e))
        return "Apologies, I'm experiencing technical difficulties. Please try again later."
