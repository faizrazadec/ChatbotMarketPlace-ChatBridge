# chatbot.py
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
    logger.info(f"Creating chatbot for user: {username}")
    conn = get_connection()
    c = conn.cursor()
    bot_id = None

    try:
        # Create initial chatbot record
        c.execute('''INSERT INTO chatbots 
                    (username, company_name, domain, industry, system_prompt, documents, created_at)
                    VALUES (?,?,?,?,?,?,?)''',
                (username, data['company_name'], data['domain'], data['industry'],
                data['system_prompt'], '', datetime.now()))
        bot_id = c.lastrowid
        logger.info(f"Created base chatbot record with ID: {bot_id}")

        # Create document directory structure
        bot_dir = os.path.join('user_docs', username, str(bot_id))
        os.makedirs(bot_dir, exist_ok=True)
        logger.info(f"Created document directory: {bot_dir}")

        # Process uploaded files
        doc_paths = []
        if files:
            for file in files:
                safe_filename = "".join(c for c in file.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
                file_path = os.path.join(bot_dir, safe_filename)
                
                # Handle duplicate filenames
                counter = 1
                while os.path.exists(file_path):
                    name, ext = os.path.splitext(safe_filename)
                    file_path = os.path.join(bot_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                with open(file_path, 'wb') as f:
                    f.write(file.getbuffer())
                doc_paths.append(file_path)
                logger.debug(f"Stored document: {file_path}")

            # Update record with document paths
            c.execute('''UPDATE chatbots SET documents = ?
                        WHERE id = ?''',
                    (','.join(doc_paths), bot_id))
        
        conn.commit()
        # Call document processing and embedding generation after files are uploaded
        process_document(bot_dir)  # Process documents and generate embeddings

        logger.info(f"Successfully created chatbot {bot_id}")
        return True

    except Exception as e:
        logger.error(f"Chatbot creation failed: {str(e)}")
        st.error(f"Error creating chatbot: {str(e)}")
        
        # Cleanup on failure
        if bot_id:
            try:
                bot_dir = os.path.join('user_docs', username, str(bot_id))
                if os.path.exists(bot_dir):
                    shutil.rmtree(bot_dir)
                logger.info(f"Cleaned up failed chatbot directory: {bot_dir}")
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed: {str(cleanup_error)}")
        
        conn.rollback()
        return False

    finally:
        conn.close()

def get_user_chatbots(username):
    """Retrieve all chatbots for a given user"""
    logger.info(f"Fetching chatbots for user: {username}")
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute('''SELECT * FROM chatbots WHERE username=?''', (username,))
        results = c.fetchall()
        logger.debug(f"Found {len(results)} chatbots for {username}")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch chatbots: {str(e)}")
        return []
    finally:
        conn.close()

def delete_chatbot(bot_id, username):
    """Permanently delete a chatbot and its associated data"""
    logger.critical(f"Deleting chatbot {bot_id} for {username}")
    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Get document paths from database
        c.execute('''SELECT documents FROM chatbots 
                    WHERE id=? AND username=?''', (bot_id, username))
        result = c.fetchone()
        doc_paths = result[0].split(',') if result and result[0] else []
        
        # Delete database records
        c.execute('''DELETE FROM chat_history 
                    WHERE bot_id=?''', (bot_id,))
        c.execute('''DELETE FROM chatbots 
                    WHERE id=? AND username=?''', (bot_id, username))
        conn.commit()
        logger.info(f"Deleted database records for chatbot {bot_id}")

        # Delete document directory
        bot_dir = os.path.join('user_docs', username, str(bot_id))
        if os.path.exists(bot_dir):
            shutil.rmtree(bot_dir)
            logger.info(f"Deleted document directory: {bot_dir}")

        # Clean up parent directories if empty
        try:
            user_dir = os.path.join('user_docs', username)
            if os.path.exists(user_dir) and not os.listdir(user_dir):
                os.rmdir(user_dir)
                logger.info(f"Removed empty user directory: {user_dir}")
        except OSError as e:
            logger.debug(f"Parent directory cleanup not needed: {str(e)}")

        return True

    except Exception as e:
        logger.error(f"Chatbot deletion failed: {str(e)}")
        st.error(f"Error deleting chatbot: {str(e)}")
        conn.rollback()
        return False

    finally:
        conn.close()

def get_chat_history(bot_id):
    """Retrieve conversation history for a chatbot"""
    logger.info(f"Fetching chat history for bot {bot_id}")
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute('''SELECT role, content 
                    FROM chat_history 
                    WHERE bot_id=? 
                    ORDER BY timestamp''', (bot_id,))
        history = [{"role": row[0], "content": row[1]} 
                for row in c.fetchall()]
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
        c.execute('''INSERT INTO chat_history 
                    (bot_id, role, content, timestamp)
                    VALUES (?,?,?,?)''',
                (bot_id, role, content, datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to save message: {str(e)}")
        return False
    finally:
        conn.close()