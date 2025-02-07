# auth.py
import sqlite3
import hashlib
import shutil
import os
import streamlit as st

from database import get_connection, validate_email
from logger import setup_logger

# Get the configured logger
logger = setup_logger()

def create_user(username: str, email: str, password: str) -> bool:
    """Create new user with email validation"""
    logger.info(f"Attempting to create user: {username}")
    if not validate_email(email):
        logger.warning(f"Invalid email format: {email}")
        raise ValueError("Invalid email format")
    
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        c.execute("INSERT INTO users VALUES (?,?,?)", 
                 (username, email.lower(), hashed_pw))
        conn.commit()
        logger.info(f"User created successfully: {username}")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"User creation failed: {str(e)}")
        if "UNIQUE constraint failed: users.email" in str(e):
            raise ValueError("Email already registered")
        elif "UNIQUE constraint failed: users.username" in str(e):
            raise ValueError("Username already exists")
        raise
    finally:
        conn.close()

def verify_user(identifier: str, password: str) -> bool:
    """Verify user by username or email"""
    logger.info(f"Verifying user: {identifier}")
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        # Try both username and email
        c.execute('''SELECT * FROM users 
                     WHERE (username=? OR email=?) AND password=?''',
                  (identifier, identifier.lower(), hashed_pw))
        result = c.fetchone()
        return result is not None
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False
    finally:
        conn.close()

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
