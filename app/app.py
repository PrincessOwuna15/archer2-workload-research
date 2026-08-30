from email.message import EmailMessage
import os
import smtplib

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(project_root, '.env'))

app = Flask(__name__, template_folder='.', static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'development-only-change-me')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/contact', methods=['POST'])
def contact():
    user_email = request.form.get('email', '').strip()
    user_message = request.form.get('message', '').strip()

    if not user_email or not user_message:
        flash('Please provide an email address and message.', 'error')
        return redirect(url_for('home', _anchor='contact'))

    email = EmailMessage()
    email['Subject'] = 'New ARCHER2 research website message'
    email['From'] = os.environ.get('SMTP_USER', '')
    email['To'] = os.environ.get('CONTACT_EMAIL', os.environ.get('SMTP_USER', ''))
    email['Reply-To'] = user_email
    email.set_content(f'From: {user_email}\n\n{user_message}')

    try:
        with smtplib.SMTP_SSL(
            os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
            int(os.environ.get('SMTP_PORT', '465')),
        ) as smtp:
            smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'].replace(' ', ''))
            smtp.send_message(email)
    except (KeyError, OSError, smtplib.SMTPException):
        app.logger.exception('Unable to send contact form email')
        flash('The message could not be sent. Please try again later.', 'error')
        return redirect(url_for('home', _anchor='contact'))

    flash('Thank you. Your message has been sent.', 'success')
    return redirect(url_for('home', _anchor='contact'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)


