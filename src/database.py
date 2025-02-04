# database.py
import sqlite3
import os

from logger import setup_logger

# Get the configured logger
logger = setup_logger()

DB_PATH = 'users.db'  # adjust the path as needed

def get_connection():
    logger.info(f"Connecting to the {DB_PATH}...")
    return sqlite3.connect(DB_PATH)

def init_db():
    logger.info(f"Initializing {DB_PATH}...")
    conn = get_connection()
    c = conn.cursor()
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    
    # Create chatbots table
    c.execute('''CREATE TABLE IF NOT EXISTS chatbots (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     bot_id TEXT UNIQUE DEFAULT (LOWER(HEX(RANDOMBLOB(16)))),
                     username TEXT,
                     company_name TEXT,
                     domain TEXT,
                     industry TEXT,
                     system_prompt TEXT,
                     documents TEXT,
                     created_at DATETIME,
                     FOREIGN KEY(username) REFERENCES users(username)
                 )''')
    
    # Create chat_history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     bot_id INTEGER,
                     role TEXT,
                     content TEXT,
                     timestamp DATETIME,
                     FOREIGN KEY(bot_id) REFERENCES chatbots(id)
                 )''')
    
    conn.commit()
    conn.close()

def init_file_storage():
    if not os.path.exists('user_docs'):
        os.makedirs('user_docs')
