import yagmail
from logger import setup_logger

logger = setup_logger()
def send_email_bot_completion(sender_email, sender_password, receiver_email, subject, body):
    # Initialize the yagmail client
    yag = yagmail.SMTP(sender_email, sender_password)

    # Send the email
    yag.send(
        to=receiver_email,
        subject=subject,
        contents=body
    )

# Example usage
sender_email = "faiz.raza.dec@gmail.com"
sender_password = "yywj vmxj mlgc ccoo"
receiver_email = "muhammad.faiz@dataropes.ai"
subject = "Test Email"
body = "This is a test email sent through Python."

try:
    send_email_bot_completion(sender_email, sender_password, receiver_email, subject, body)
    logger.critical("Email Sended")
except Exception as e:
    logger.error(f'{e}')