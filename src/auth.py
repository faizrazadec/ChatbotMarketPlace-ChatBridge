"""
# auth.py
Authentication module for user management.

This module provides functions for user authentication, including user 
registration, login verification, and account deletion.
"""

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
    """
    Create a new user with email validation.

    Args:
        username (str): The chosen username.
        email (str): The user's email address.
        password (str): The user's password (hashed before storage).

    Returns:
        bool: True if the user is successfully created, False otherwise.
    """
    logger.info("Attempting to create user: %s", username)
    if not validate_email(email):
        logger.warning("Invalid email format: %s ", email)
        raise ValueError("Invalid email format")

    conn = get_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()

    try:
        c.execute(
            "INSERT INTO users VALUES (?,?,?)", (username, email.lower(), hashed_pw)
        )
        conn.commit()
        logger.info("User created successfully: %s", username)
        return True
    except sqlite3.IntegrityError as e:
        logger.error("User creation failed: %s", str(e))
        if "UNIQUE constraint failed: users.email" in str(e):
            raise ValueError("Email already registered") from e
        if "UNIQUE constraint failed: users.username" in str(e):
            raise ValueError("Username already exists") from e
        raise
    finally:
        conn.close()


def verify_user(identifier: str, password: str) -> bool:
    """
    Verify a user by username or email.

    Args:
        identifier (str): The username or email.
        password (str): The user's password.

    Returns:
        bool: True if credentials are correct, False otherwise.
    """
    logger.info("Verifying user: %s", identifier)
    conn = get_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()

    try:
        # Try both username and email
        c.execute(
            """SELECT * FROM users 
                     WHERE (username=? OR email=?) AND password=?""",
            (identifier, identifier.lower(), hashed_pw),
        )
        result = c.fetchone()
        return result is not None
    except sqlite3.DatabaseError as e:
        logger.error("Verification failed: %s", str(e))
        return False
    finally:
        conn.close()


def delete_user_account(username):
    """
    Delete a user account and all related data.

    This function removes the user from the database, deletes their associated chatbots 
    and chat history, and removes their user directory.

    Args:
        username (str): The username of the account to delete.

    Returns:
        bool: True if deletion is successful, False otherwise.
    """
    logger.critical("Deleting account %s", username)
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
        user_dir = os.path.join("user_docs", username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)

        return True
    except sqlite3.DatabaseError as e:
        st.error(f"Database error while deleting account: {str(e)}")
        logger.error("Database error while deleting account: %s", str(e))
        return False
    except OSError as e:
        st.error(f"File system error while deleting account: {str(e)}")
        logger.error("File system error while deleting account: %s", str(e))
        return False
    finally:
        conn.close()
