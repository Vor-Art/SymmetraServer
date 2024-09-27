from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, abort, jsonify
import os
import base64
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
MODEL_FOLDER = 'models'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MODEL_FOLDER'] = MODEL_FOLDER

def get_model_directories(user_name):
    model_dirs = []
    model_path = os.path.join(app.root_path, MODEL_FOLDER, user_name)
    for model_name in os.listdir(model_path):
        model_dir = os.path.join(model_path, model_name)
        if os.path.exists(os.path.join(model_dir, 'model.obj')):
            model_dirs.append(model_name)
    return model_dirs


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
    # return render_template('index.html')
    # return redirect(url_for('login'))
    session['logged_in'] = True
    session['username'] = "preview"
    session_date = datetime.now().strftime('%Y%m%d_%H%M%S')
    session['photo_session_date'] = session_date
    session_name = request.form.get('session_name', '')
    if not session_name:
        session_name = f"Session_{session_date}"
    else:
        session_name = f"{session_name}_{session_date}"
    session['photo_session_name'] = session_name
    return redirect(url_for('camera'))

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
    return redirect(url_for('camera'))

@app.route('/uploads/<username>/<session_name>/<filename>')
@login_required
def uploaded_file(username, session_name, filename):
    directory = os.path.join(UPLOAD_FOLDER, username, session_name)
    return send_from_directory(directory, filename)

@app.route('/observe_the_models', methods=['POST'])
@login_required
def observe_the_models():
    return redirect(url_for('view_results'))

# from flask import send_from_directory

# Serve images from the 'models/preview' directory
@app.route('/models/preview/<path:filename>')
def serve_preview_image(filename):
    return send_from_directory('models/preview', filename)

@app.route('/view_results')
@login_required
def view_results():
    username = session['username']
    sessions = get_model_directories(username)
    return render_template('intermediate.html', username=username, sessions=sessions)

@app.route('/view/<model_name>')
def view_model(model_name):
    username = session['username']
    scale_value = 1.0  # Default value in case of an issue reading the file
    try:
        with open(f"models/{username}/{model_name}/scale.txt", 'r') as file:
            scale_value = float(file.read().strip())
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading scale value: {e}, try default")

    print(f"{model_name=} {username=}, {scale_value=}")
    print(f"models/{username}/{model_name}/model.obj")

    return render_template('view_image.html', username=username, model_name=model_name, scale_value=scale_value)

@app.route('/compare', methods=['POST'])
def compare():
    model1 = request.form.get('model1')
    model2 = request.form.get('model2')
    if not model1 or not model2 or model1 == model2:
        return redirect(url_for('intermediate'))
    model1_path = os.path.join(model1, 'model.obj')
    model2_path = os.path.join(model2, 'model.obj')
    return render_template('compare.html', model1=model1_path, model2=model2_path)

@app.route('/run_python_function', methods=['POST'])
def run_python_function():
    my_python_function()
    return jsonify({'status': 'Function executed successfully'})

def my_python_function():
    # Example Python function logic
    print("Python function executed!")
    print("Python function executed!")
    print("Python function executed!")
    print("Python function executed!")


if __name__ == '__main__':
    app.run(host='0.0.0.0', ssl_context=('cert.pem', 'key.pem'), debug=True)