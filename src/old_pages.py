# pages.py
import streamlit as st
from database import get_connection
from auth import create_user, verify_user, delete_user_account
from chatbot import create_chatbot, get_user_chatbots, delete_chatbot
from chat_history import get_chat_history, save_message
from bot_interaction import get_bot_response
from metric import compute_avg_response_time
from embed_code import display_embed_code

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
                    # Ensure no chatbot is selected upon login.
                    st.session_state.current_bot = None
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
            'bot_name': st.text_input("Bot Name"),
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
            st.markdown(
                """
                <div style="background-color:#d4edda; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb;">
                    <h3 style="color:#155724; margin-bottom: 0;">Thank you for using ChatBridge!</h3>
                    <p style="color:#155724;">Your chatbot will be ready soon. Once created you'll receive an email.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if not data['company_name'] or not data['system_prompt']:
                st.error("Fields marked with * are required!")
            else:
                if create_chatbot(st.session_state.current_user, data, data['files']):
                    # Clear any previous bot selection after creating a new bot.
                    st.session_state.current_bot = None
                    if 'creating_bot' in st.session_state:
                        del st.session_state.creating_bot
                    st.session_state.bot_created = True
                    st.rerun()
                    # Show a pop-up message indicating successful creation.
                    # if st.session_state.bot_created:
                    #     st.markdown(
                    #         """
                    #         <div style="background-color:#d4edda; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb;">
                    #             <h3 style="color:#155724; margin-bottom: 0;">Thank you for using ChatBridge!</h3>
                    #             <p style="color:#155724;">Your chatbot will be ready soon. Once created you'll receive an email.</p>
                    #         </div>
                    #         """,
                    #         unsafe_allow_html=True
                    #     )
                    # if st.form_submit_button("OK"):
                    #     st.session_state.bot_created = False  # Reset pop-up state
                    #     # Ensure that the current bot is cleared so that the welcome page is shown.
                    #     st.session_state.current_bot = None
                    #     st.rerun()  # Redirect to the home page

def main_app():
    logger.info("Function main_app.")
    st.set_page_config(page_title="ChatBridge", page_icon="🤖")
    
    # Initialize session state variables if they don't exist.
    if 'current_bot' not in st.session_state:
        st.session_state.current_bot = None  # Do not auto-select any bot.
    if 'messages' not in st.session_state:
        st.session_state.messages = {}
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None
    if 'delete_account' not in st.session_state:
        st.session_state.delete_account = False
    if 'creating_bot' not in st.session_state:
        st.session_state.creating_bot = False
    if 'show_embed_script' not in st.session_state:
        st.session_state.show_embed_script = False

    with st.sidebar:
        # Inject custom CSS for sidebar layout.
        st.markdown(
            """
            <style>
            /* Container for the entire sidebar with fixed height */
            .fixed-sidebar {
                position: relative;
                overflow: hidden;
                padding: 10px;
            }
            /* Scrollable container for the bot list */
            .bot-list {
                max-height: 300px;  /* Adjust height as needed */
                overflow-y: auto;
                padding-right: 10px; /* provide space for scrollbar */
            }
            /* Fixed footer at the bottom of the sidebar */
            .sidebar-footer {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                padding: 10px;
                background-color: white; /* match your sidebar background */
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Wrap the entire sidebar content in a fixed container.
        st.markdown('<div class="fixed-sidebar">', unsafe_allow_html=True)

        ## Fixed header & bot list portion
        st.header(f"Welcome, {st.session_state.current_user}")
        st.subheader("Your Chatbots")
        
        # Scrollable bot list container
        st.markdown('<div class="bot-list">', unsafe_allow_html=True)
        chatbots = get_user_chatbots(st.session_state.current_user)
        
        if chatbots:
            for bot in chatbots:
                cols = st.columns([4, 1])
                with cols[0]:
                    if st.button(
                        f"{bot[2]}",
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
        st.markdown('</div>', unsafe_allow_html=True)  # End of bot-list container

        # Button to display embed code if a bot is selected
        if st.session_state.current_bot:
            if st.button("Get Embed Code"):
                st.session_state.show_embed_script = True
                st.rerun()

        ## Fixed footer portion
        st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
        
        # Delete confirmation for a bot (if active)
        if st.session_state.get("delete_confirm"):
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

        # Create new chatbot button
        if st.button("+ Create New Chatbot"):
            st.session_state.current_bot = None
            st.session_state.creating_bot = True

        st.markdown("<br><br>", unsafe_allow_html=True)
        st.subheader("Account Settings")
        
        if st.button("Delete My Account"):
            st.session_state.delete_account = True
            
        if st.session_state.get("delete_account"):
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
        
        st.markdown('</div>', unsafe_allow_html=True)  # End of sidebar-footer container
        st.markdown('</div>', unsafe_allow_html=True)  # End of fixed-sidebar container


    chatbots = get_user_chatbots(st.session_state.current_user)
    
    # Main area: if embed script flag is set, display embed code.
    if st.session_state.get("show_embed_script", False):
        display_embed_code()
        return  # Stop further rendering of the main dashboard.

    # If no chatbots exist, show a welcome message and prompt to create one.
    if not chatbots:
        if st.session_state.get('creating_bot', False):
            st.session_state.current_bot = None
            st.markdown("# Create Your First Chatbot 🚀")
            chatbot_creation_form()
        else:
            st.markdown("# Welcome to TOPdesk AI Bot! 🤖")
            st.divider()
            st.subheader("You don't have any chatbots yet")
            st.write("Get started by creating your first AI-powered chatbot!")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                if st.button("✨ Create New Bot", type="primary"):
                    st.session_state.current_bot = None
                    st.session_state.creating_bot = True
                    st.rerun()
            
            st.image("https://cdn-icons-png.flaticon.com/512/1055/1055666.png", width=200)
            st.write("Need help getting started? [Read our guide](https://example.com)")
    
    # If the user is in the process of creating a chatbot.
    elif st.session_state.get('creating_bot', False):
        st.session_state.current_bot = None
        st.markdown("# Create New Chatbot 🛠️")
        chatbot_creation_form()
    
    # Otherwise, if chatbots exist and the user is not creating a new one...
    else:
        # Only show the chat dashboard if a chatbot has been selected.
        if not st.session_state.current_bot:
            st.markdown("# Welcome to ChatBridge!")
            st.write("Please select a chatbot from the sidebar to view your conversation history.")
        else:
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
                avg_response_time = compute_avg_response_time(st.session_state.messages[bot_id])
                st.metric("Avg. Response Time", avg_response_time)
            with col3:
                total_interactions = len(st.session_state.messages[bot_id])
                st.metric("Total Interactions", total_interactions)
            
            for message in st.session_state.messages.get(bot_id, []):
                if "role" == 'user':
                    with st.chat_message(message["role"], avatar='/home/faizraza/Projects/chatbot_market_place/data/9802824.jpg'):
                        st.markdown(message["content"])
                else:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
            
            if prompt := st.chat_input("Ask about tickets, services, or support..."):
                # Save the user message locally and in the DB
                st.session_state.messages[bot_id].append({"role": "user", "content": prompt})
                with st.chat_message("user", avatar='/home/faizraza/Projects/chatbot_market_place/data/9802824.jpg'):
                    st.markdown(prompt)
                save_message(bot_id, "user", prompt)
                # print(current_bot)
                # Extract bot configuration details from the current bot record.
                bot_name = current_bot[2]
                company_name = current_bot[4]
                domain = current_bot[5]
                industry = current_bot[5]
                bot_behavior = current_bot[7]
                
                # Create a session id unique for this conversation
                session_id = f"{st.session_state.current_user}_{bot_id}"
                logger.error(f"{session_id}")
                logger.warning(f"botid: {session_id}")
                
                # Get the dynamic AI response using the LangChain chain
                ai_response = get_bot_response(
                    bot_name,
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
