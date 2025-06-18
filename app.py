import os
from flask import Flask, render_template, redirect, url_for, session, request
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret')

# Database connection (example, adjust as needed)
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = None
if DATABASE_URL:
    try:
        conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print("Database connection failed:", e)

@app.route('/')
def index():
    # Example: render dashboard, pass user info
    user = {'name': 'Demo User'}
    return render_template('dashboard.html', user=user)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

# Add other routes as needed

if __name__ == '__main__':
    app.run(debug=True)