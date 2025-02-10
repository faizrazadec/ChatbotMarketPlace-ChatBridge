"""
This module handles automated email notifications using yagmail.
It fetches user emails from the database and sends chatbot completion notifications.
"""

import yagmail
import os
from dotenv import load_dotenv
from database import get_connection

load_dotenv()

sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")

subject = "Your Chat bot is ready to play with"
body = """
    Dear,
    We are pleased to inform you that your chatbot is now ready to be
    deployed and interacted with. Our team has worked diligently to ensure
    that your chatbot meets the highest standards of functionality and user
    experience.
    Your chatbot has been trained on a robust dataset and is equipped with
    advanced natural language processing capabilities. It is designed to
    provide accurate and helpful responses to user queries, and its
    intuitive interface makes it easy to navigate.
    To get started with your chatbot, simply [insert instructions or
    link to access the chatbot]. If you have any questions or require
    further assistance, please do not hesitate to contact us.
    We are confident that your chatbot will provide significant value
    to your users and look forward to receiving your feedback.
    Best regards,
    ChatBridge
    """


# Define the email-sending function using yagmail
def send_email_bot_completion(
    sender_email, sender_password, receiver_email, subject, body
):
    """
    Sends an email notification to the given receiver email using yagmail.

    Args:
        receiver_email (str): The recipient's email address.
    """
    # Initialize the yagmail client
    yag = yagmail.SMTP(sender_email, sender_password)

    # Send the email
    yag.send(to=receiver_email, subject=subject, contents=body)

def get_email_for_username(username):
    """
    Fetches the email address associated with a given username from the database.

    Args:
        username (str): The username to look up.

    Returns:
        str or None: The user's email if found, else None.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None
