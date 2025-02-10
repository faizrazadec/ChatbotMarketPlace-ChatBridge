"""
# chatbot.py
Chatbot management module.

This module handles chatbot creation, retrieval, deletion, 
and chat history storage for users.
"""

import os
import shutil
from datetime import datetime
import streamlit as st
from document_processor import process_document  # Import the process_document function
from database import get_connection
from logger import setup_logger

logger = setup_logger()


def create_chatbot(username, data, files):
    """Create a new chatbot with organized document storage"""
    logger.info("Creating chatbot for user: %s", username)
    conn = get_connection()
    c = conn.cursor()
    bot_id = None

    try:
        # Create initial chatbot record
        c.execute(
            """INSERT INTO chatbots 
                (username, bot_name, company_name, domain, industry, system_prompt, documents, created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
            (
                username,
                data["bot_name"],
                data["company_name"],
                data["domain"],
                data["industry"],
                data["system_prompt"],
                "",
                datetime.now(),
            ),
        )
        bot_id = c.lastrowid
        bot_name = data["bot_name"]
        logger.info("Created base chatbot record with ID: %s", bot_id)

        # Create document directory structure
        bot_dir = os.path.join("user_docs", username, str(bot_name))
        os.makedirs(bot_dir, exist_ok=True)
        logger.info("Created document directory: %s", bot_dir)

        # Process uploaded files
        doc_paths = []
        if files:
            for file in files:
                safe_filename = "".join(
                    c for c in file.name if c.isalnum() or c in (" ", ".", "_")
                ).rstrip()
                file_path = os.path.join(bot_dir, safe_filename)

                # Handle duplicate filenames
                counter = 1
                while os.path.exists(file_path):
                    name, ext = os.path.splitext(safe_filename)
                    file_path = os.path.join(bot_dir, f"{name}_{counter}{ext}")
                    counter += 1

                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                doc_paths.append(file_path)
                logger.debug("Stored document: %s", file_path)

            # Update record with document paths
            c.execute(
                """UPDATE chatbots SET documents = ?
                        WHERE id = ?""",
                (",".join(doc_paths), bot_id),
            )

        conn.commit()
        # Call document processing and embedding generation after files are uploaded
        process_document(bot_dir)  # Process documents and generate embeddings

        logger.info("Successfully created chatbot %s", bot_id)
        return True


    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        st.error(f"Error creating chatbot: {str(e)}")

        # Cleanup on failure
        if bot_id:
            try:
                bot_dir = os.path.join("user_docs", username, str(bot_id))
                if os.path.exists(bot_dir):
                    shutil.rmtree(bot_dir)
                logger.info("Cleaned up failed chatbot directory: %s", bot_dir)
            except Exception as cleanup_error:
                logger.error("Cleanup failed: %s", str(cleanup_error))

        conn.rollback()
        return False

    finally:
        conn.close()


def get_user_chatbots(username):
    """Retrieve all chatbots for a given user"""
    logger.info("Fetching chatbots for user: %s", username)
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute("""SELECT * FROM chatbots WHERE username=?""", (username,))
        results = c.fetchall()
        logger.debug("Found %s chatbots for %s", len(results), username)
        return results
    except Exception as e:
        logger.error("Failed to fetch chatbots: %s", str(e))
        return []
    finally:
        conn.close()


def delete_chatbot(bot_id, username):
    """Permanently delete a chatbot and its associated data"""
    logger.critical("Deleting chatbot %s for %s", bot_id, username)
    conn = get_connection()
    c = conn.cursor()

    try:
        # Get document paths from database
        c.execute(
            """SELECT documents FROM chatbots 
                    WHERE id=? AND username=?""",
            (bot_id, username),
        )
        result = c.fetchone()
        doc_paths = result[0].split(",") if result and result[0] else []

        # Delete database records
        c.execute(
            """DELETE FROM chat_history 
                    WHERE bot_id=?""",
            (bot_id,),
        )
        c.execute(
            """DELETE FROM chatbots 
                    WHERE id=? AND username=?""",
            (bot_id, username),
        )
        conn.commit()
        logger.info("Deleted database records for chatbot %s", bot_id)

        # Delete document directory
        bot_dir = os.path.join("user_docs", username, str(bot_id))
        if os.path.exists(bot_dir):
            shutil.rmtree(bot_dir)
            logger.info("Deleted document directory: %s", bot_dir)

        # Clean up parent directories if empty
        try:
            user_dir = os.path.join("user_docs", username)
            if os.path.exists(user_dir) and not os.listdir(user_dir):
                os.rmdir(user_dir)
                logger.info("Removed empty user directory: %s", str(e))
        except OSError as e:
            logger.debug("Parent directory cleanup not needed: %s", user_dir)

        return True

    except Exception as e:
        logger.error("Chatbot deletion failed: %s", str(e))
        st.error(f"Error deleting chatbot: {str(e)}")
        conn.rollback()
        return False

    finally:
        conn.close()


def get_chat_history(bot_id):
    """Retrieve conversation history for a chatbot"""
    logger.info("Fetching chat history for bot %s", bot_id)
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute(
            """SELECT role, content 
                    FROM chat_history 
                    WHERE bot_id=? 
                    ORDER BY timestamp""",
            (bot_id,),
        )
        history = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
        logger.debug("Found %s messages in history", len(history))
        return history
    except Exception as e:
        logger.error("Failed to fetch chat history: %s", str(e))
        return []
    finally:
        conn.close()


def save_message(bot_id, role, content):
    """Store a message in chat history"""
    logger.debug("Saving {role} message for bot %s", bot_id)
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute(
            """INSERT INTO chat_history 
                    (bot_id, role, content, timestamp)
                    VALUES (?,?,?,?)""",
            (bot_id, role, content, datetime.now()),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error("Failed to save message: %s", str(e))
        return False
    finally:
        conn.close()
