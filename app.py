import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import random
from datetime import datetime, UTC, timedelta, timezone
from dotenv import load_dotenv
import secrets

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
db_path = os.path.join(instance_dir, 'chasedown.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(instance_dir, 'uploads')

db = SQLAlchemy(app)

def has_eye_power(user_id):
    eye = EyeInTheSky.query.filter_by(user_id=user_id).first()
    if eye:
        eye_time = eye.start_time.replace(tzinfo=timezone.utc) if eye.start_time.tzinfo is None else eye.start_time
        elapsed = (datetime.now(timezone.utc) - eye_time).total_seconds()
        if elapsed <= 300:
            return True
        else:
            db.session.delete(eye)
            db.session.commit()
    return False

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), default='runner')
    points = db.Column(db.Integer, default=0)
    active_task_id = db.Column(db.Integer, db.ForeignKey('task.id'))

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

class ActivePowerup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    user = db.relationship('User', backref='active_powerup')

class OracleRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80))
    recipient = db.Column(db.String(80))
    question = db.Column(db.Text)
    answer = db.Column(db.String(10))
    resolved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

class EyeInTheSky(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now())

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

    pending_oracle = OracleRequest.query.filter_by(recipient=user.username, resolved=False).first()
    if pending_oracle:
        return redirect(url_for('oracle_receive'))

    if user.role == 'admin':
        users = User.query.all()
        videos = TaskInstance.query.filter(TaskInstance.completed == True).all()
        return render_template('admin.html', users=users, videos=videos)

    # --- Eye Timer ---
    eye_expiry_time = None
    eye = EyeInTheSky.query.filter_by(user_id=user.id).first()
    if eye:
        eye_time = eye.start_time.replace(tzinfo=timezone.utc) if eye.start_time.tzinfo is None else eye.start_time
        elapsed = (datetime.now(timezone.utc) - eye_time).total_seconds()
        if elapsed < 300:
            eye_expiry_time = (eye_time + timedelta(seconds=300)).isoformat()
        else:
            db.session.delete(eye)
            db.session.commit()

    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()

    return render_template(
        'dashboard.html',
        user=user,
        task=task_instance,
        eye_expiry_time=eye_expiry_time
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
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if task_instance:
        return redirect(url_for('task_page'))
    all_tasks = Task.query.all()
    if len(all_tasks) < 2:
        return "Not enough tasks in the database. Please run init_db.py."
    options = random.sample(all_tasks, 2)
    has_ante = ActivePowerup.query.filter_by(user_id=user.id, name='up_the_ante').first() is not None
    return render_template('task_choice.html', tasks=options, powerup=has_ante)

@app.route('/choose_task/<int:task_id>')
def choose_task(task_id):
    user = User.query.get(session['user_id'])
    task = Task.query.get(task_id)
    if not task:
        return "Task not found."
    instance = TaskInstance(user_id=user.id, task_id=task.id)
    db.session.add(instance)
    db.session.commit()
    return redirect(url_for('task_page'))

@app.route('/task')
def task_page():
    
    user = User.query.get(session['user_id'])
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if not task_instance:
        return redirect(url_for('home'))
    task = Task.query.get(task_instance.task_id)
    has_ante = ActivePowerup.query.filter_by(user_id=user.id, name='up_the_ante').first() is not None

    start_time = task_instance.timestamp.replace(tzinfo=timezone.utc).isoformat()
    time_limit = task.time_limit

    return render_template(
        'task.html',
        task=task,
        powerup=has_ante,
        start_time=start_time,
        time_limit=time_limit
    )

@app.route('/submit', methods=['POST'])
def submit():
    file = request.files['video']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    user = User.query.get(session['user_id'])
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    task_instance.video_filename = filename
    task_instance.completed = True
    base_points = Task.query.get(task_instance.task_id).points
    powerup = ActivePowerup.query.filter_by(user_id=user.id, name='up_the_ante').first()
    if powerup:
        user.points += base_points * 2
        db.session.delete(powerup)
    else:
        user.points += base_points
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/fail', methods=['POST'])
def fail():
    user = User.query.get(session['user_id'])
    task_instance = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if task_instance:
        task = Task.query.get(task_instance.task_id)
        powerup = ActivePowerup.query.filter_by(user_id=user.id, name='up_the_ante').first()
        if powerup:
            user.points -= task.points * 2
            db.session.delete(powerup)
        else:
            user.points -= task.points // 2
        db.session.delete(task_instance)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/buy_powerup', methods=['POST'])
def buy_powerup():
    user = User.query.get(session['user_id'])
    powerup = request.form['powerup']
    active_task = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    if powerup == 'up_the_ante':
        if active_task or ActivePowerup.query.filter_by(user_id=user.id, name='up_the_ante').first():
            return "You already have an active challenge or power-up."
        if user.points >= 20:
            user.points -= 20
            db.session.add(ActivePowerup(user_id=user.id, name='up_the_ante'))
            db.session.commit()
        return redirect(url_for('store'))
    elif powerup == 'insight':
        if user.points >= 1:
            user.points -= 1
            db.session.commit()
            return redirect(url_for('insight_page'))
    elif powerup == 'oracle':
        cost = 5 if user.role == 'runner' else 3
        if user.points >= cost:
            user.points -= cost
            db.session.commit()
            return redirect(url_for('oracle_send'))
    elif powerup == 'eye':
        cost = 20 if user.role == 'runner' else 15
        if user.points >= cost:
            user.points -= cost
            existing = EyeInTheSky.query.filter_by(user_id=user.id).first()
            if existing:
                db.session.delete(existing)
            db.session.add(EyeInTheSky(user_id=user.id, start_time=datetime.now(timezone.utc)))
            db.session.commit()
            return redirect(url_for('store'))

    return redirect(url_for('store'))

@app.route('/store')
def store():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    active_task = TaskInstance.query.filter_by(user_id=user.id, completed=False).first()
    has_ante = ActivePowerup.query.filter_by(user_id=user.id, name="up_the_ante").first() is not None

    # Determine if Eye in the Sky is still active
    eye = EyeInTheSky.query.filter_by(user_id=user.id).first()
    has_eye = False
    if eye:
        elapsed = (datetime.utcnow() - eye.start_time.replace(tzinfo=None)).total_seconds()
        if elapsed <= 300:
            has_eye = True
        else:
            db.session.delete(eye)
            db.session.commit()

    return render_template('store.html',
        user=user,
        active_task=active_task,
        has_ante=has_ante,
        has_eye=has_eye  # pass only this
    )

@app.route('/insight')
def insight_page():
    users = User.query.order_by(User.points.desc()).all()
    powerups = ActivePowerup.query.all()
    powerup_map = {p.user_id: p.name for p in powerups}
    return render_template('insight.html', users=users, user_powerups=powerup_map)

@app.route('/oracle_send', methods=['GET', 'POST'])
def oracle_send():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        recipient = request.form['target']
        question = request.form['question']
        existing = OracleRequest.query.filter_by(recipient=recipient, resolved=False).first()
        if existing:
            return "Target already has an unanswered Oracle question."
        request_entry = OracleRequest(sender=user.username, recipient=recipient, question=question)
        db.session.add(request_entry)
        db.session.commit()
        return redirect(url_for('oracle_result', oracle_id=request_entry.id))
    users = User.query.all()
    return render_template('oracle_send.html', users=users, user=user)

@app.route('/oracle_receive')
def oracle_receive():
    user = User.query.get(session['user_id'])
    pending = OracleRequest.query.filter_by(recipient=user.username, resolved=False).first()
    if pending:
        return render_template('oracle_receive.html', oracle=pending)
    return redirect(url_for('home'))

@app.route('/oracle_answer/<int:oracle_id>', methods=['POST'])
def oracle_answer(oracle_id):
    oracle = OracleRequest.query.get(oracle_id)
    oracle.answer = request.form['answer']
    oracle.resolved = True
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/oracle_result/<int:oracle_id>')
def oracle_result(oracle_id):
    oracle = OracleRequest.query.get(oracle_id)
    return render_template('oracle_result.html', oracle=oracle)

@app.route('/map')
def map_page():
    user = User.query.get(session['user_id'])
    show_all = has_eye_power(user.id)
    coordinates = []

    if show_all:
        coords = UserCoordinates.query.all()
        for c in coords:
            player = User.query.get(c.user_id)
            if player and player.username != user.username:
                coordinates.append({
                    'username': player.username,
                    'lat': c.lat,
                    'lon': c.lon,
                    'role': player.role
                })

    return render_template('map.html', show_all=show_all, others=coordinates)

@app.route('/gps_map')
def gps_map():
    user = User.query.get(session['user_id'])
    eye = EyeInTheSky.query.filter_by(user_id=user.id).first()
    if not eye or (datetime.now(UTC) - eye.start_time).total_seconds() > 300:
        return redirect(url_for('home'))

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
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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

if __name__ == '__main__':
    db_path = os.path.join('instance', 'chasedown.db')
    if not os.path.exists(db_path):
        print("Database not found. Running init_db.py...")
        subprocess.run(['python', os.path.join('instance', 'init_db.py')])

    with app.app_context():
        db.create_all()
        run_init_script()
    app.run(debug=True, host='0.0.0.0')
