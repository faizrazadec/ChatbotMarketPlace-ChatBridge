import streamlit as st
import sqlite3
import hashlib
import os
import shutil
from datetime import datetime

# Database setup
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS chatbots
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT,
              company_name TEXT,
              domain TEXT,
              industry TEXT,
              system_prompt TEXT,
              documents TEXT,
              created_at DATETIME,
              FOREIGN KEY(username) REFERENCES users(username))''')
c.execute('''CREATE TABLE IF NOT EXISTS chat_history
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              bot_id INTEGER,
              role TEXT,
              content TEXT,
              timestamp DATETIME,
              FOREIGN KEY(bot_id) REFERENCES chatbots(id))''')
conn.commit()
conn.close()

# File storage setup
if not os.path.exists('user_docs'):
    os.makedirs('user_docs')

def create_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users VALUES (?,?)", (username, hashed_pw))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pw))
    result = c.fetchone()
    conn.close()
    return result is not None

def create_chatbot(username, data, files):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    doc_paths = []
    if files:
        user_dir = os.path.join('user_docs', username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        
        for file in files:
            file_path = os.path.join(user_dir, file.name)
            with open(file_path, 'wb') as f:
                f.write(file.getbuffer())
            doc_paths.append(file_path)
    
    try:
        c.execute('''INSERT INTO chatbots 
                     (username, company_name, domain, industry, system_prompt, documents, created_at)
                     VALUES (?,?,?,?,?,?,?)''',
                  (username, data['company_name'], data['domain'], data['industry'],
                   data['system_prompt'], ','.join(doc_paths), datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating chatbot: {str(e)}")
        return False
    finally:
        conn.close()

def get_user_chatbots(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM chatbots WHERE username=?", (username,))
    results = c.fetchall()
    conn.close()
    return results

def get_chat_history(bot_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE bot_id=? ORDER BY timestamp", (bot_id,))
    history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return history

def save_message(bot_id, role, content):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (bot_id, role, content, timestamp) VALUES (?,?,?,?)",
              (bot_id, role, content, datetime.now()))
    conn.commit()
    conn.close()

def delete_chatbot(bot_id, username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT documents FROM chatbots WHERE id=? AND username=?", (bot_id, username))
        docs = c.fetchone()[0]
        
        c.execute("DELETE FROM chatbots WHERE id=? AND username=?", (bot_id, username))
        conn.commit()
        
        if docs:
            for doc_path in docs.split(','):
                if os.path.exists(doc_path):
                    if os.path.isfile(doc_path):
                        os.remove(doc_path)
                    elif os.path.isdir(doc_path):
                        shutil.rmtree(doc_path)
        
        user_dir = os.path.join('user_docs', username)
        if os.path.exists(user_dir) and not os.listdir(user_dir):
            os.rmdir(user_dir)
            
        return True
    except Exception as e:
        st.error(f"Error deleting chatbot: {str(e)}")
        return False
    finally:
        conn.close()

def delete_user_account(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT id FROM chatbots WHERE username=?", (username,))
        bot_ids = [row[0] for row in c.fetchall()]
        
        for bot_id in bot_ids:
            c.execute("DELETE FROM chat_history WHERE bot_id=?", (bot_id,))
        
        c.execute("DELETE FROM chatbots WHERE username=?", (username,))
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        
        user_dir = os.path.join('user_docs', username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            
        return True
    except Exception as e:
        st.error(f"Error deleting account: {str(e)}")
        return False
    finally:
        conn.close()

def login_page():
    st.title("TOPdesk AI Bot Login")
    
    menu = st.selectbox("Menu", ["Login", "Sign Up"])
    
    if menu == "Login":
        with st.form("Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.current_user = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    else:
        with st.form("Sign Up"):
            new_user = st.text_input("New Username")
            new_pw = st.text_input("New Password", type="password")
            if st.form_submit_button("Create Account"):
                if create_user(new_user, new_pw):
                    st.success("Account created! Please login using the menu")
                else:
                    st.error("Username already exists")

def chatbot_creation_form():
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
        
        if st.form_submit_button("Create Chatbot"):
            if not data['company_name'] or not data['system_prompt']:
                st.error("Fields marked with * are required!")
            else:
                if create_chatbot(st.session_state.current_user, data, data['files']):
                    st.success("Chatbot created successfully!")
                    if 'creating_bot' in st.session_state:
                        del st.session_state.creating_bot
                    st.rerun()

def main_app():
    st.set_page_config(page_title="TOPdesk AI Bot Demo", page_icon="🤖")
    
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
                        f"{bot[2]} ({bot[3]})",
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
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Delete", type="primary"):
                    if delete_chatbot(bot_id, st.session_state.current_user):
                        st.success("Chatbot deleted!")
                        if st.session_state.current_bot and st.session_state.current_bot[0] == bot_id:
                            del st.session_state.current_bot
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
            
        st.divider()
        
        st.subheader("Account Settings")
        if st.button("Delete My Account"):
            st.session_state.delete_account = True
            
        if st.session_state.delete_account:
            st.warning("**Danger Zone** - This action cannot be undone!")
            with st.form("Delete Account"):
                password = st.text_input("Confirm Password", type="password")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Permanently Delete Account"):
                        if verify_user(st.session_state.current_user, password):
                            if delete_user_account(st.session_state.current_user):
                                st.success("Account deleted successfully!")
                                st.session_state.clear()
                                st.rerun()
                        else:
                            st.error("Incorrect password")
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.delete_account = False
            st.divider()
        
        if st.button("Logout"):
            del st.session_state.logged_in
            del st.session_state.current_user
            st.rerun()
        
        st.divider()
        st.header("TOPdesk Integration")
        st.success("Connected to TOPdesk Instance: **prod-ACME**")
        st.write("**Last Sync:** 2 mins ago")
        st.write("**Tickets Handled Today:** 142")

    chatbots = get_user_chatbots(st.session_state.current_user)
    
    if not chatbots:
        if hasattr(st.session_state, 'creating_bot'):
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
    
    elif hasattr(st.session_state, 'creating_bot'):
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
            st.metric("Total Conversations", conv_count, "Today")
        with col2:
            st.metric("Resolution Rate", "89%", "+5% from last week")
        with col3:
            st.metric("User Satisfaction", "4.8★", "92% positive")
        
        for message in st.session_state.messages.get(bot_id, []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask about tickets, services, or support..."):
            st.session_state.messages[bot_id].append({"role": "user", "content": prompt})
            save_message(bot_id, "user", prompt)
            
            ai_response = f"{current_bot[5]}\n\n*Based on: {current_bot[2]} ({current_bot[3]})*"
            if "agent" in prompt.lower():
                ai_response += "\n\n[Transfer to human agent requested]"
            
            st.session_state.messages[bot_id].append({"role": "assistant", "content": ai_response})
            save_message(bot_id, "assistant", ai_response)
            
            st.rerun()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main_app()
else:
    login_page()