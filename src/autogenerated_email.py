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
    We are pleased to inform you that your chatbot is now ready to be deployed and interacted with. Our team has worked diligently to ensure that your chatbot meets the highest standards of functionality and user experience.
    Your chatbot has been trained on a robust dataset and is equipped with advanced natural language processing capabilities. It is designed to provide accurate and helpful responses to user queries, and its intuitive interface makes it easy to navigate.
    To get started with your chatbot, simply [insert instructions or link to access the chatbot]. If you have any questions or require further assistance, please do not hesitate to contact us.
    We are confident that your chatbot will provide significant value to your users and look forward to receiving your feedback.
    Best regards,
    ChatBridge
    """

# Define the email-sending function using yagmail
def send_email_bot_completion(sender_email, sender_password, receiver_email, subject, body):
    # Initialize the yagmail client
    yag = yagmail.SMTP(sender_email, sender_password)

    # Send the email
    yag.send(
        to=receiver_email,
        subject=subject,
        contents=body
    )

# (Optional) If your login accepts usernames, you may need a helper function to get the user’s email.
def get_email_for_username(username):
    # This function should query your database to return the email for the given username.
    # Here’s an example using SQLite:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

dd = get_email_for_username('faizraza')
print(dd)