# pages.py
import streamlit as st
from database import get_connection
from auth import create_user, verify_user, delete_user_account
from chatbot import create_chatbot, get_user_chatbots, delete_chatbot
from chat_history import get_chat_history, save_message
from bot_interaction import get_bot_response
from metric import compute_avg_response_time

from logger import setup_logger

# Get the configured logger
logger = setup_logger()

def login_page():
    logger.info("Function login_page.")
    st.title("TOPdesk AI Bot Login")
    
    menu = st.selectbox("Menu", ["Login", "Sign Up"])
    
    if menu == "Login":
        with st.form("Login"):
            identifier = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                # First try verifying by username directly
                if verify_user(identifier, password):
                    st.session_state.logged_in = True
                    if "@" in identifier:
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE email = ?", (identifier.lower(),))
                        result = c.fetchone()
                        conn.close()
                        if result:
                            st.session_state.current_user = result[0]
                            st.rerun()
                    else:
                        st.session_state.current_user = identifier
                        st.rerun()
                else:
                    st.error("Invalid credentials")
    
    else:
        with st.form("Sign Up"):
            new_user = st.text_input("New Username")
            new_email = st.text_input("Email")
            new_pw = st.text_input("New Password", type="password")
            submitted = st.form_submit_button("Create Account")
            if submitted:
                try:
                    if create_user(new_user, new_email, new_pw):
                        st.success("Account created! Please login using the menu")
                    else:
                        st.error("Username already exists")
                except ValueError as e:
                    st.error(str(e))

def chatbot_creation_form():
    if 'bot_created' not in st.session_state:
        st.session_state.bot_created = False

    logger.info("Function chatbot_creation_form.")

    with st.form("Create Chatbot"):
        st.subheader("Create New Chatbot")

        data = {
            'company_name': st.text_input("Company Name*"),
            'domain': st.selectbox("Domain*", ["Customer Support", "Sales", "HR", "IT Helpdesk", "Other"]),
            'industry': st.selectbox("Industry*", ["Technology", "Healthcare", "Finance", "Education", "Retail", "Other"]),
            'system_prompt': st.text_area("Bot Behavior Description*", 
                                          help="Describe how the bot should behave and respond to users"),
            'files': st.file_uploader("Upload Knowledge Documents", 
                                      type=['pdf', 'txt', 'docx'], 
                                      accept_multiple_files=True)
        }

        submitted = st.form_submit_button("Create Chatbot")

        if submitted:
            if not data['company_name'] or not data['system_prompt']:
                st.error("Fields marked with * are required!")
            else:
                if create_chatbot(st.session_state.current_user, data, data['files']):
                    if 'creating_bot' in st.session_state:
                        del st.session_state.creating_bot
                    st.session_state.bot_created = True
                    # Show the pop-up if chatbot is created
                    if st.session_state.bot_created:
                        st.markdown(
                            """
                            <div style="background-color:#d4edda; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb;">
                                <h3 style="color:#155724; margin-bottom: 0;">Thank you for using ChatBridge!</h3>
                                <p style="color:#155724;">Your chatbot will be ready soon. Once created you'll receive an email.</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    if st.form_submit_button("OK"):
                        st.session_state.bot_created = False  # Reset pop-up state
                        st.rerun()  # Redirect to the home page


def main_app():
    logger.info("Function main_app.")
    st.set_page_config(page_title="ChatBridge", page_icon="🤖")
    
    if 'current_bot' not in st.session_state:
        st.session_state.current_bot = None
    if 'messages' not in st.session_state:
        st.session_state.messages = {}
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None
    if 'delete_account' not in st.session_state:
        st.session_state.delete_account = False

    with st.sidebar:
        st.header(f"Welcome, {st.session_state.current_user}")
        st.subheader("Your Chatbots")
        chatbots = get_user_chatbots(st.session_state.current_user)
        
        if chatbots:
            for bot in chatbots:
                cols = st.columns([4,1])
                with cols[0]:
                    if st.button(
                        f"{bot[3]} Bot",
                        help=f"Created: {bot[7]}\nIndustry: {bot[4]}",
                        key=f"bot_{bot[0]}"
                    ):
                        st.session_state.current_bot = bot
                        st.session_state.messages[bot[0]] = get_chat_history(bot[0])
                        st.rerun()
                with cols[1]:
                    if st.button("🗑️", key=f"del_{bot[0]}"):
                        st.session_state.delete_confirm = bot[0]
            
            st.divider()
        
        if st.session_state.delete_confirm:
            bot_id = st.session_state.delete_confirm
            st.warning("Are you sure you want to delete this chatbot?")
            logger.warning("Are you sure you want to delete this chatbot?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Delete", type="primary"):
                    if delete_chatbot(bot_id, st.session_state.current_user):
                        st.success("Chatbot deleted!")
                        logger.critical("Chatbot deleted!")
                        if st.session_state.current_bot and st.session_state.current_bot[0] == bot_id:
                            st.session_state.current_bot = None
                        if bot_id in st.session_state.messages:
                            del st.session_state.messages[bot_id]
                        st.session_state.delete_confirm = None
                        st.rerun()
            with col2:
                if st.button("Cancel"):
                    st.session_state.delete_confirm = None
            st.divider()
        
        if st.button("+ Create New Chatbot"):
            st.session_state.creating_bot = True
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.divider()
        
        st.subheader("Account Settings")
        if st.button("Delete My Account"):
            st.session_state.delete_account = True
            
        if st.session_state.delete_account:
            st.warning("**Danger Zone** - This action cannot be undone!")
            logger.warning("**Danger Zone** - This action cannot be undone!")
            with st.form("Delete Account"):
                password = st.text_input("Confirm Password", type="password")
                col1, col2 = st.columns(2)
                if st.form_submit_button("Permanently Delete Account"):
                    if verify_user(st.session_state.current_user, password):
                        from auth import delete_user_account
                        if delete_user_account(st.session_state.current_user):
                            st.success("Account deleted successfully!")
                            logger.critical("Account deleted successfully!")
                            st.session_state.clear()
                            st.rerun()
                    else:
                        st.error("Incorrect password")
                        logger.error("Incorrect password")
                if st.form_submit_button("Cancel"):
                    st.session_state.delete_account = False
            st.divider()

        if st.button("Logout"):
            del st.session_state.logged_in
            del st.session_state.current_user
            st.rerun()
        st.divider()

    chatbots = get_user_chatbots(st.session_state.current_user)
    
    if not chatbots:
        if st.session_state.get('creating_bot', False):
            st.markdown("# Create Your First Chatbot 🚀")
            chatbot_creation_form()
        else:
            st.markdown("# Welcome to TOPdesk AI Bot! 🤖")
            st.divider()
            st.subheader("You don't have any chatbots yet")
            st.write("Get started by creating your first AI-powered chatbot!")
            
            col1, col2 = st.columns([1,2])
            with col1:
                if st.button("✨ Create New Bot", type="primary"):
                    st.session_state.creating_bot = True
                    st.rerun()
            
            st.image("https://cdn-icons-png.flaticon.com/512/1055/1055666.png", width=200)
            st.write("Need help getting started? [Read our guide](https://example.com)")
    
    elif st.session_state.get('creating_bot', False):
        st.markdown("# Create New Chatbot 🛠️")
        chatbot_creation_form()
    
    else:
        if not st.session_state.current_bot:
            st.session_state.current_bot = chatbots[-1]
        
        current_bot = st.session_state.current_bot
        bot_id = current_bot[0]
        
        if bot_id not in st.session_state.messages:
            st.session_state.messages[bot_id] = get_chat_history(bot_id)
        
        st.markdown(f"# {current_bot[2]} Chatbot Dashboard")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            conv_count = len([m for m in st.session_state.messages[bot_id] if m['role'] == 'user'])
            st.metric("Total Conversations", conv_count)
        with col2:
            # Average Response Time: computed from the stored timestamps.
            avg_response_time = compute_avg_response_time(st.session_state.messages[bot_id])
            st.metric("Avg. Response Time", avg_response_time)
        with col3:
            # Total Interactions: the total count of messages in this conversation.
            total_interactions = len(st.session_state.messages[bot_id])
            st.metric("Total Interactions", total_interactions)
        
        for message in st.session_state.messages.get(bot_id, []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask about tickets, services, or support..."):
            # Save the user message locally and in the DB
            st.session_state.messages[bot_id].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            save_message(bot_id, "user", prompt)
            
            # Extract bot configuration from the database record.
            # Adjust these indexes if your DB schema changes:
            # (id, username, company_name, domain, industry, system_prompt, documents, created_at)
            company_name = current_bot[2]
            domain = current_bot[3]
            industry = current_bot[4]
            bot_behavior = current_bot[5]
            
            # Create a session id unique for this conversation
            session_id = f"{st.session_state.current_user}_{bot_id}"
            logger.error(f"{session_id}")
            logger.warning(f"botid: {session_id}")
            
            # Get the dynamic AI response using the LangChain chain
            ai_response = get_bot_response(
            company_name,
            domain,
            industry,
            bot_behavior,
            prompt,
            session_id,
            bot_id,
            username=st.session_state.current_user
        )
            
            st.session_state.messages[bot_id].append({"role": "assistant", "content": ai_response})
            
            save_message(bot_id, "assistant", ai_response)
            
            st.rerun()
