# bot_interaction.py
import os
from dotenv import load_dotenv

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_redis import RedisChatMessageHistory

from logger import setup_logger

load_dotenv()
logger = setup_logger()

# Use the environment variable if set, otherwise default to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
logger.info(f"Connecting to Redis at: {REDIS_URL}")

gemini_api_key = os.getenv('GEMINI_API_KEY')
llm = ChatGoogleGenerativeAI(
    model='gemini-1.5-flash',
    api_key=gemini_api_key
)

def build_system_prompt(company_name: str, domain: str, industry: str, bot_behavior: str) -> str:
    """
    Build a system prompt template based on the chatbot configuration.
    """
    logger.info(f"Building System Prompt...")
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
    """
    Return a Redis-backed message history instance for the given session.
    """
    logger.info("Fetching Redis history.")
    return RedisChatMessageHistory(session_id, redis_url=REDIS_URL)

def get_bot_response(company_name: str, domain: str, industry: str, bot_behavior: str, user_input: str, session_id: str) -> str:
    """
    Given a bot’s configuration and the user input, construct the prompt,
    run the chain (with history) and return the AI response.
    """
    logger.info(f"Hold on. Getting Bot response...")
    # Build a system prompt from the chatbot's configuration
    system_prompt_template = build_system_prompt(company_name, domain, industry, bot_behavior)
    
    # Construct the LangChain prompt using the dynamic system prompt
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt_template),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}")
    ])
    
    # Build the chain: prompt -> LLM -> output parser
    chain = prompt | llm | StrOutputParser()
    
    # Create a runnable that supports message history via Redis
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_redis_history,
        input_messages_key="input",
        history_messages_key="history"
    )
    
    # Invoke the chain with the user's input and a session_id that uniquely identifies the conversation.
    result = chain_with_history.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": session_id}},
    )
    
    return result
