
from app import db, User, Task, TaskInstance, app

with app.app_context():
    print("\n--- USERS ---")
    users = User.query.all()
    for user in users:
        print(f"{user.id}: {user.username} | Role: {user.role} | Points: {user.points}")

    print("\n--- TASKS ---")
    tasks = Task.query.all()
    for task in tasks:
        print(f"{task.id}: {task.name} ({task.points} pts)")

    print("\n--- SUBMITTED VIDEOS ---")
    submissions = TaskInstance.query.filter_by(completed=True).all()
    for s in submissions:
        user = User.query.get(s.user_id)
        task = Task.query.get(s.task_id)
        print(f"{user.username} submitted '{task.name}': {s.video_filename}")
