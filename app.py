import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import random
from datetime import datetime, UTC, timedelta, timezone
from dotenv import load_dotenv
import secrets
import urllib.parse
import time

def run_init_script():
    """Import init.py only AFTER app & db exist."""
    import init           # local import avoids circular loop
    init.run()            # call its seeding function

# --- Ensure 'instance/' folder exists early ---
basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)

# Path to .env
env_path = ".env"

# If .env doesn't exist, create it with a secure SECRET_KEY
if not os.path.exists(env_path):
    secret_key = secrets.token_urlsafe(32)
    with open(env_path, "w") as f:
        f.write(f"SECRET_KEY={secret_key}\n")
    print("[INFO] .env file created with a secure SECRET_KEY.")
else:
    print("[INFO] .env file found.")

# Load the .env file
load_dotenv(env_path)

# --- App setup ---
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
db_path = os.path.join('/mnt/uploads', 'chasedown.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('/mnt/uploads', 'uploads')

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), default='runner')
    points = db.Column(db.Integer, default=0)
    active_task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    last_point_loss = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    locked_until = db.Column(db.DateTime, nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    description = db.Column(db.Text)
    points = db.Column(db.Integer)
    time_limit = db.Column(db.Integer, default=1200)

class TaskInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    completed = db.Column(db.Boolean, default=False)
    video_filename = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', backref='task_instances')
    task = db.relationship('Task')

class UserCoordinates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)

# --- Routes ---
@app.route('/')
def start():
    return render_template('start.html')

@app.route('/dashboard')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.role == 'admin':
        users = User.query.all()
        videos = TaskInstance.query.filter(TaskInstance.completed == True).all()
        return render_template('admin.html', users=users, videos=videos)
    
    # Tipped lockout check
    if user.role != 'admin' and user.locked_until:
        locked_time = user.locked_until
        if locked_time.tzinfo is None:
            locked_time = locked_time.replace(tzinfo=timezone.utc)

        now = datetime.now(UTC)
        if now < locked_time:
            seconds_left = int((locked_time - now).total_seconds())
            return render_template('tipped_cooldown.html', seconds_left=seconds_left, user=user)
        else:
            user.locked_until = None
            db.session.commit()

    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()

    # Provide players for hunter to tip
    players_to_tip = []
    if user.role == 'hunter':
        players_to_tip = User.query.filter(User.username != 'admin', User.id != user.id).all()

    return render_template(
        'dashboard.html',
        user=user,
        task=task_instance,
        players_to_tip=players_to_tip,
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            return "Username already taken"
        user = User(username=request.form['username'], password=request.form['password'])
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/tasks')
def tasks():
    user = User.query.get(session['user_id'])

    if user.role == 'hunter':
        return render_template('hunter_blocked.html', user=user)

    # If player already has an assigned task, redirect
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if task_instance:
        return redirect(url_for('task_page'))

    # If tasks are already stored in session, reuse them
    if 'task_choices' in session:
        task_ids = session['task_choices']
        options = Task.query.filter(Task.id.in_(task_ids)).all()
    else:
        all_tasks = Task.query.all()
        if len(all_tasks) < 2:
            return "Not enough tasks in the database. Please run init_db.py."
        options = random.sample(all_tasks, 2)
        session['task_choices'] = [t.id for t in options]

    return render_template('task_choice.html', tasks=options)

@app.route('/choose_task/<int:task_id>')
def choose_task(task_id):
    user = User.query.get(session['user_id'])

    # Only allow choosing from the two stored options
    valid_choices = session.get('task_choices')
    if not valid_choices or task_id not in valid_choices:
        return "Invalid task selection.", 400

    task = Task.query.get(task_id)
    if not task:
        return "Task not found."

    instance = TaskInstance(user_id=user.id, task_id=task.id)
    db.session.add(instance)
    db.session.commit()

    # Clear the choices so they can't reuse them
    session.pop('task_choices', None)

    return redirect(url_for('task_page'))

@app.route('/task')
def task_page():
    user = User.query.get(session['user_id'])
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if user.role == 'hunter':
        return render_template('hunter_blocked.html', user=user)

    if not task_instance:
        return redirect(url_for('home'))
    task = Task.query.get(task_instance.task_id)

    start_time = task_instance.timestamp.replace(tzinfo=timezone.utc).isoformat()
    time_limit = task.time_limit

    return render_template(
        'task.html',
        task=task,
        start_time=start_time,
        time_limit=time_limit
    )

@app.route('/submit', methods=['POST'])
def submit():
    start_time = time.time()

    file = request.files['video']
    filename = secure_filename(file.filename)

    user = User.query.get(session['user_id'])
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()

    if file and (time.time() - start_time <= 6):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        task_instance.video_filename = filename
    else:
        task_instance.video_filename = None  # Or some placeholder text like 'timeout'

    task_instance.completed = True
    base_points = Task.query.get(task_instance.task_id).points
    user.points += base_points
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/fail', methods=['POST'])
def fail():
    user = User.query.get(session['user_id'])
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if task_instance:
        task = Task.query.get(task_instance.task_id)
        user.points -= task.points // 2
        db.session.delete(task_instance)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/map')
def map_page():
    user = User.query.get(session['user_id'])

    coordinates = []

    coords = UserCoordinates.query.all()
    for c in coords:
        player = User.query.get(c.user_id)

        if not player or player.username == 'admin':
            continue  # Never show admin

        if user.role in ('hunter', 'admin'):
            # Show all players except admin
            coordinates.append({
                'username': player.username,
                'lat': c.lat,
                'lon': c.lon,
                'role': player.role,
                'is_self': player.id == user.id
            })
        elif player.id == user.id:
            # Runners see only themselves
            coordinates.append({
                'username': player.username,
                'lat': c.lat,
                'lon': c.lon,
                'role': player.role,
                'is_self': True
            })

    return render_template('map.html', others=coordinates)

@app.route('/leaderboard')
def leaderboard():
    users = User.query.filter(User.username != 'admin').order_by(User.points.desc()).all()
    leaderboard_data = []

    for user in users:
        # Find an unfinished task instance for this user
        task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
        task_name = task_instance.task.name if task_instance and task_instance.task else '—'

        leaderboard_data.append({
            'username': user.username,
            'points': user.points,
            'role': user.role,
            'task': task_name
        })

    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/gps_map')
def gps_map():
    user = User.query.get(session['user_id'])

    # Get all users + last known coordinates
    coordinates = UserCoordinates.query.all()
    return render_template('gps_map.html', coordinates=coordinates)

@app.route('/update_location', methods=['POST'])
def update_location():
    user = User.query.get(session['user_id'])
    lat = request.form['lat']
    lon = request.form['lon']
    coord = UserCoordinates.query.filter_by(user_id=user.id).first()
    if not coord:
        coord = UserCoordinates(user_id=user.id, lat=lat, lon=lon)
        db.session.add(coord)
    else:
        coord.lat = lat
        coord.lon = lon
    db.session.commit()
    return '', 204

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Find the TaskInstance using this filename
    instance = TaskInstance.query.filter_by(video_filename=filename).first()
    if not instance:
        return "Video not found.", 404

    user = User.query.get(instance.user_id)
    task = Task.query.get(instance.task_id)

    # Extract the extension (e.g., .mp4, .mov, .webm)
    _, ext = os.path.splitext(filename)

    # Build safe custom filename
    safe_username = urllib.parse.quote(user.username)
    safe_task = urllib.parse.quote(task.name.replace(' ', '_'))
    new_name = f"{safe_username}-{safe_task}-{task.points}{ext}"

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    return send_file(
        filepath,
        as_attachment=True,
        download_name=new_name
    )

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user.username == 'admin':
        return "Can't delete admin"
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/change_role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    new_role = request.form['role']
    user = User.query.get(user_id)
    user.role = new_role
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/change_points/<int:user_id>', methods=['POST'])
def change_points(user_id):
    user = User.query.get(user_id)
    user.points = int(request.form['points'])
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete_video/<int:instance_id>', methods=['POST'])
def delete_video(instance_id):
    instance = TaskInstance.query.get(instance_id)
    if instance:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], instance.video_filename))
        except:
            pass
        db.session.delete(instance)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/toggle_lock', methods=['POST'])
def toggle_lock():
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return "Access denied", 403

    action = request.form.get('action')

    if action == 'lock':
        # Lock all non-admin users indefinitely (use far-future date)
        future = datetime.now(UTC) + timedelta(days=3650)  # 10 years
        User.query.filter(User.role != 'admin').update({User.locked_until: future})
    elif action == 'unlock':
        User.query.filter(User.role != 'admin').update({User.locked_until: None})

    db.session.commit()
    return redirect(url_for('home'))

@app.route('/drain_hunter_points', methods=['POST'])
def drain_hunter_points():
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return "Access denied", 403

    hunters = User.query.filter_by(role='hunter').all()
    for hunter in hunters:
        lost = hunter.points // 10
        hunter.points -= lost

    db.session.commit()
    return redirect(url_for('home'))

@app.route('/tip', methods=['POST'])
def tip():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != 'hunter':
        return "Only hunters can tip players.", 403

    target_username = request.form.get('target_username')
    target = User.query.filter_by(username=target_username).first()

    if not target or target.username == 'admin':
        return "Invalid target.", 400

    user.role = 'runner'
    target.role = 'hunter'

    target.locked_until = datetime.now(UTC) + timedelta(minutes=2)

    db.session.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    db_path = os.path.join('instance', 'chasedown.db')
    app.run(debug=True, host='0.0.0.0')
