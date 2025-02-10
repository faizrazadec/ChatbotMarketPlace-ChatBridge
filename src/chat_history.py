"""
# chat_history.py
Chat History Management Module

This module handles the retrieval and storage of chatbot conversations.
"""

from datetime import datetime

from database import get_connection
from logger import setup_logger

# Get the configured logger
logger = setup_logger()


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
    logger.debug("Saving %s message for bot %s", role, bot_id)
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
