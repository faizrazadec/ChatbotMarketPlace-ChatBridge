import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_redis import RedisChatMessageHistory
from logger import setup_logger
import sqlite3

load_dotenv()

company_name= "TechSolutions"
domain= "IT support"
industry= "Enterprise Software"
bot_behavior= "Friendly but technical assistant that explains complex concepts simply"

system_prompt_template = f"""**Company Identity**
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

# Get the configured logger
logger = setup_logger()

# Use the environment variable if set, otherwise default to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
logger.info(f"Connecting to Redis at: {REDIS_URL}")

history = RedisChatMessageHistory(
    session_id="001",
    redis_url=REDIS_URL
)

gemini_api_key = os.getenv('GEMINI_API_KEY')

llm = ChatGoogleGenerativeAI(
    model = 'gemini-1.5-flash',
    api_key=gemini_api_key
)

prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_prompt_template),
    MessagesPlaceholder(variable_name = "history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

chain = prompt | llm | StrOutputParser()

# Function to get or create a RedisChatMessageHistory instance
def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    logger.info("Fetching History.")
    return RedisChatMessageHistory(session_id, redis_url=REDIS_URL)

# Create a runnable with message history
chain_with_history = RunnableWithMessageHistory(
    chain, get_redis_history, input_messages_key="input", history_messages_key="history"
)

def get_input():
    """Asks the user for a joke topic."""
    logger.critical("Waiting for the `user_input`")
    topic = input()
    return topic

# Update your chatbot creation form processing
def create_chatbot(username, data, files):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Generate system prompt from user inputs
    system_prompt = f"""**Company Identity**
    You are an AI representative of {data['company_name']}, operating in the {data['industry']} industry with a focus on {data['domain']}. 

    **Core Behavior Guidelines**
    1. Adhere strictly to this persona: {data['system_prompt']}
    2. Maintain professional communication aligned with {data['industry']} standards
    3. Specialize in {data['domain']}-related knowledge while acknowledging other areas
    4. Adapt tone to match user's communication style while staying professional
    5. If unsure about information, offer to follow up rather than speculate

    **Interaction Protocol**
    - Begin interactions with: "Welcome to {data['company_name']}! How can I assist you today?"
    - Format responses using clear, concise paragraphs with industry-appropriate terminology
    - Escalate complex requests through proper channels when necessary
    - Maintain {data['industry']}-compliant confidentiality standards

    **Domain-Specific Adaptation**
    Incorporate common {data['industry']} practices and {data['domain']} operational knowledge naturally into responses without explicit mention.

    **Boundary Clause**
    If asked about topics outside {data['domain']} or {data['industry']}, respond: "I specialize in {data['domain']} for {data['company_name']}. For other inquiries, please visit our website or contact support."
    """

def main():
    """Gets the joke topic from the user and prints a joke about it."""
    user_input = get_input()
    logger.info("Responsing...")
    res = chain_with_history.invoke(
        {"input": {user_input}},
        config={"configurable": {"session_id": "alice_123"}},
    )
    logger.error(res)

if __name__ == "__main__":
    main()