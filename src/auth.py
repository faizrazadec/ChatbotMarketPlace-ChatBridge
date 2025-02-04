# auth.py
import sqlite3
import hashlib
import shutil
import os
import streamlit as st

from database import get_connection
from logger import setup_logger

# Get the configured logger
logger = setup_logger()

def create_user(username, password):
    logger.info(f"Creating User {username} account...")
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users VALUES (?,?)", (username, hashed_pw))
        conn.commit()
        logger.info(f"Successfully Created {username} Account.")
        return True
    except sqlite3.IntegrityError:
        logger.error(f"Error while creating the {username} account...")
        return False
    finally:
        conn.close()

def verify_user(username, password):
    logger.critical(f"Verifing {username} Credentials...")
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pw))
    result = c.fetchone()
    conn.close()
    return result is not None

def delete_user_account(username):
    logger.critical(f"Deleting {username} account...")
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Get all chatbot ids for this user
        c.execute("SELECT id FROM chatbots WHERE username=?", (username,))
        bot_ids = [row[0] for row in c.fetchall()]
        
        for bot_id in bot_ids:
            c.execute("DELETE FROM chat_history WHERE bot_id=?", (bot_id,))
        
        c.execute("DELETE FROM chatbots WHERE username=?", (username,))
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
        
        # Delete user's file directory
        user_dir = os.path.join('user_docs', username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            
        return True
    except Exception as e:
        st.error(f"Error deleting account: {str(e)}")
        logger.error(f"Error deleting account: {str(e)}")
        return False
    finally:
        conn.close()
