from flask_mail import Message
from flask import current_app

# local imports
from core import mail

def send_email(to, subject, template):
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            html=template,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise e  # correct Python syntax