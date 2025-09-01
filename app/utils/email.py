from flask import current_app, render_template, url_for
from flask_mail import Message
from app import mail
import threading

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body):
    """Send email with async option"""
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=text_body,
        html=html_body
    )
    
    # Send asynchronously in production
    if current_app.config.get('TESTING'):
        mail.send(msg)
    else:
        thread = threading.Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        )
        thread.start()

def send_verification_email(user, token):
    """Send email verification"""
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    
    send_email(
        subject='Verify Your Email Address',
        recipients=[user.email],
        text_body=render_template('emails/verify_email.txt', 
                                user=user, verify_url=verify_url),
        html_body=render_template('emails/verify_email.html', 
                                user=user, verify_url=verify_url)
    )

def send_password_reset_email(user, token):
    """Send password reset email"""
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    send_email(
        subject='Reset Your Password',
        recipients=[user.email],
        text_body=render_template('emails/reset_password.txt',
                                user=user, reset_url=reset_url),
        html_body=render_template('emails/reset_password.html',
                                user=user, reset_url=reset_url)
    )