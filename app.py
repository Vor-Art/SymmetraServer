from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import base64
import time
from functools import wraps
from datetime import timedelta
from database import database
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure random key
app.permanent_session_lifetime = timedelta(minutes=30)

# Configuration for file uploads
UPLOAD_FOLDER = 'photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Default user credentials
USERNAME = 'user'
PASSWORD = 'pass'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            session_id = str(uuid.uuid4())[:8]
            session['photo_session_id'] = session_id
            session['photo_session_name'] = 'Session_' + session_id
            return redirect(url_for('camera'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/new_session', methods=['GET', 'POST'])
@login_required
def new_session():
    if request.method == 'POST':
        # Start a new photo session with a name
        session_id = str(uuid.uuid4())[:8]
        session_name = request.form['session_name']
        if not session_name:
            session_name = 'Session_' + session_id
        else:
            session_name = f"{session_name}_{session_id}"
        session['photo_session_id'] = session_id
        session['photo_session_name'] = session_name
        return redirect(url_for('camera'))
    return render_template('new_session.html')

@app.route('/camera')
@login_required
def camera():
    username = session['username']
    session_id = session['photo_session_id']
    session_name = session['photo_session_name']
    # Get list of photos from current session
    current_session_dir = os.path.join(UPLOAD_FOLDER, username, session_name)
    current_photos = []
    if os.path.exists(current_session_dir):
        current_photos = os.listdir(current_session_dir)
    # Get list of previous sessions
    user_dir = os.path.join(UPLOAD_FOLDER, username)
    sessions = []
    if os.path.exists(user_dir):
        sessions = [(d, os.listdir(os.path.join(user_dir, d))) for d in os.listdir(user_dir)]
    return render_template('camera.html', session_id=session_id, session_name=session_name, current_photos=current_photos, sessions=sessions)

@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'image' in request.form:
        # Handle image from webcam capture
        data_url = request.form['image']
        header, encoded = data_url.split(',', 1)
        data = base64.b64decode(encoded)

        username = session['username']
        session_name = session['photo_session_name']
        directory = os.path.join(UPLOAD_FOLDER, username, session_name)

        if not os.path.exists(directory):
            os.makedirs(directory)

        filename = f'{int(time.time())}.png'
        filepath = os.path.join(directory, filename)

        with open(filepath, 'wb') as f:
            f.write(data)
        return 'Photo saved successfully'
    elif 'file' in request.files:
        # Handle uploaded file
        file = request.files['file']
        if file and allowed_file(file.filename):
            username = session['username']
            session_name = session['photo_session_name']
            directory = os.path.join(UPLOAD_FOLDER, username, session_name)
            if not os.path.exists(directory):
                os.makedirs(directory)
            filename = secure_filename(file.filename)
            filepath = os.path.join(directory, filename)
            file.save(filepath)
            return redirect(url_for('camera'))
        else:
            return 'Invalid file type'
    return 'No image data received'

@app.route('/download_photo/<session_name>/<filename>')
@login_required
def download_photo(session_name, filename):
    username = session['username']
    directory = os.path.join(UPLOAD_FOLDER, username, session_name)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/uploads/<username>/<session_name>/<filename>')
@login_required
def uploaded_file(username, session_name, filename):
    directory = os.path.join(UPLOAD_FOLDER, username, session_name)
    return send_from_directory(directory, filename)

@app.route('/add_previous_photo', methods=['POST'])
@login_required
def add_previous_photo():
    current_session_name = session['photo_session_name']
    username = session['username']
    source_session_name = request.form['session_name']
    filename = request.form['filename']
    source_directory = os.path.join(UPLOAD_FOLDER, username, source_session_name)
    target_directory = os.path.join(UPLOAD_FOLDER, username, current_session_name)
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    source_path = os.path.join(source_directory, filename)
    target_path = os.path.join(target_directory, filename)
    if os.path.exists(source_path):
        import shutil
        shutil.copy(source_path, target_path)
    return redirect(url_for('camera'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'))
