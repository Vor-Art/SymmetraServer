from flask import Flask, render_template, request, redirect, url_for, session
import os
import base64
import time
from functools import wraps
from datetime import timedelta
from database import database
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure random key
app.permanent_session_lifetime = timedelta(minutes=30)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in database['users'].keys() and password == database['users'][username]['pass']:
            session['logged_in'] = True
            session['username'] = username
            # Initialize a new photo session
            session['photo_session_id'] = str(uuid.uuid4())
            return redirect(url_for('camera'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/new_session')
@login_required
def new_session():
    # Start a new photo session
    session['photo_session_id'] = str(uuid.uuid4())
    return redirect(url_for('camera'))

@app.route('/camera')
@login_required
def camera():
    return render_template('camera.html', session_id=session['photo_session_id'])

@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    data_url = request.form['image']
    header, encoded = data_url.split(',', 1)
    data = base64.b64decode(encoded)

    username = session['username']
    photo_session_id = session['photo_session_id']
    directory = os.path.join('photos', username, photo_session_id)

    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = f'{int(time.time())}.png'
    filepath = os.path.join(directory, filename)

    with open(filepath, 'wb') as f:
        f.write(data)
    return 'Photo saved successfully'

if __name__ == '__main__':
    app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'))
