# chat_history.py
from datetime import datetime

from database import get_connection
from logger import setup_logger

# Get the configured logger
logger = setup_logger()


def get_chat_history(bot_id):
    """Retrieve conversation history for a chatbot"""
    logger.info(f"Fetching chat history for bot {bot_id}")
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
        logger.debug(f"Found {len(history)} messages in history")
        return history
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {str(e)}")
        return []
    finally:
        conn.close()


def save_message(bot_id, role, content):
    """Store a message in chat history"""
    logger.debug(f"Saving {role} message for bot {bot_id}")
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
        logger.error(f"Failed to save message: {str(e)}")
        return False
    finally:
        conn.close()
