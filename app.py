from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import os
import base64
import time
from functools import wraps
from datetime import timedelta, datetime
from database import database
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure random key
app.permanent_session_lifetime = timedelta(minutes=30)

# Configuration for file uploads
UPLOAD_FOLDER = 'photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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
            session_date = datetime.now().strftime('%Y%m%d_%H%M%S')
            session['photo_session_date'] = session_date
            session_name = request.form.get('session_name', '')
            if not session_name:
                session_name = f"Session_{session_date}"
            else:
                session_name = f"{session_name}_{session_date}"
            session['photo_session_name'] = session_name
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
        session_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_name = request.form['session_name']
        if not session_name:
            session_name = f"Session_{session_date}"
        else:
            session_name = f"{session_name}_{session_date}"
        session['photo_session_date'] = session_date
        session['photo_session_name'] = session_name
        return redirect(url_for('camera'))
    return render_template('new_session.html')

@app.route('/camera')
@login_required
def camera():
    username = session['username']
    session_name = session['photo_session_name']
    # Get list of photos from current session
    current_session_dir = os.path.join(UPLOAD_FOLDER, username, session_name)
    current_photos = []
    if os.path.exists(current_session_dir):
        current_photos = os.listdir(current_session_dir)
    # Get list of previous sessions and their photos
    user_dir = os.path.join(UPLOAD_FOLDER, username)
    sessions = []
    if os.path.exists(user_dir):
        for sess_name in os.listdir(user_dir):
            if sess_name != session_name:
                sess_dir = os.path.join(user_dir, sess_name)
                photos = os.listdir(sess_dir)
                sessions.append({'name': sess_name, 'photos': photos})
    return render_template('camera.html', session_name=session_name, current_photos=current_photos, sessions=sessions)

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

        # Updated filename generation with microseconds
        filename = f'{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.png'
        filepath = os.path.join(directory, filename)

        with open(filepath, 'wb') as f:
            f.write(data)
        return 'Photo saved successfully'
    elif 'files[]' in request.files:
        # Handle batch file uploads
        files = request.files.getlist('files[]')
        username = session['username']
        session_name = session['photo_session_name']
        directory = os.path.join(UPLOAD_FOLDER, username, session_name)
        if not os.path.exists(directory):
            os.makedirs(directory)
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(directory, filename)
                file.save(filepath)
        return redirect(url_for('camera'))
    return 'No image data received'

@app.route('/download_photos', methods=['POST'])
@login_required
def download_photos():
    selected_photos = request.form.getlist('selected_photos[]')
    session_name = request.form.get('session_name')
    username = session['username']
    directory = os.path.join(UPLOAD_FOLDER, username, session_name)
    # Create a ZIP file of the selected photos
    if selected_photos:
        zip_filename = f"{session_name}_photos.zip"
        zip_filepath = os.path.join('temp', zip_filename)
        os.makedirs('temp', exist_ok=True)
        import zipfile
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for filename in selected_photos:
                file_path = os.path.join(directory, filename)
                zipf.write(file_path, arcname=filename)
        return send_from_directory('temp', zip_filename, as_attachment=True)
    return redirect(url_for('camera'))

@app.route('/add_photos_to_current_session', methods=['POST'])
@login_required
def add_photos_to_current_session():
    selected_photos = request.form.getlist('selected_photos[]')
    source_session_name = request.form.get('session_name')
    username = session['username']
    current_session_name = session['photo_session_name']
    source_directory = os.path.join(UPLOAD_FOLDER, username, source_session_name)
    target_directory = os.path.join(UPLOAD_FOLDER, username, current_session_name)
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    for filename in selected_photos:
        source_path = os.path.join(source_directory, filename)
        target_path = os.path.join(target_directory, filename)
        if os.path.exists(source_path):
            shutil.copy(source_path, target_path)
    return redirect(url_for('camera'))

@app.route('/delete_session', methods=['POST'])
@login_required
def delete_session():
    session_name = request.form.get('session_name')
    username = session['username']
    directory = os.path.join(UPLOAD_FOLDER, username, session_name)
    if os.path.exists(directory):
        shutil.rmtree(directory)
        # Optionally, remove the session from the list
        # You may also want to add a flash message to confirm deletion
    return redirect(url_for('camera'))

@app.route('/uploads/<username>/<session_name>/<filename>')
@login_required
def uploaded_file(username, session_name, filename):
    directory = os.path.join(UPLOAD_FOLDER, username, session_name)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'))
