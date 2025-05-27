from app import db, User, Task, app

with app.app_context():
    db.create_all()

    # Admin setup
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='lavender*123', role='admin', points=0)
        db.session.add(admin)
        print("Admin user created.")
    else:
        print("Admin user already exists.")

    # Task setup
    existing_tasks = {task.name for task in Task.query.all()}
    tasks_to_add = [
        Task(name='Hunt the Hunters', description='Video the Hunters for 1 min without them noticing. They must always be on video and clearly visible.', points=40),
        Task(name='High Five', description='Find another pair of Runners and give them a high five. You both gain 10 points.', points=10),
        Task(name='Out in the Open', description='Stand out in an open area for 2 mins with no blockages within 15m and only sparse bushland within 30m.', points=30),
        Task(name='Get Rich', description="Find strangers' money, make effort to return it. Must not know who found it. 30 min limit.", points=40),
        Task(name='Become a Comedian', description='Tell a joke to a stranger who looks over 15. They must hear it properly.', points=20),
        Task(name='Bush Survival 101', description='Build a bush shelter from scratch. Post picture on group chat. 30 min limit.', points=40),
        Task(name='Just Dance', description='Do a full dance for at least 1.5 mins without moving from spot.', points=30),
        Task(name='In Plain Sight', description='Stay in area with 5+ people within 15m for 5 minutes.', points=30),
        Task(name='Team Player', description='Join a stranger’s game for 5+ minutes. Must play actively. 30 min to find a game.', points=50),
        Task(name='Pushup Prowess', description='Challenge a stranger to a pushup contest and they must engage.', points=40),
        Task(name='Cats or Dogs', description='Survey 20 people on cats vs dogs. Record results and post in GC.', points=30),
        Task(name='Where are you Max?', description='Find a pet/person named Max who is a stranger.', points=50),
        Task(name='The Way of the Pig', description='One partner must piggyback the other for 2 mins.', points=30),
        Task(name='Moosuiance', description='Pretend to be a cow (moo & crawl) near a stranger for 30s.', points=10),
        Task(name='Echo Chamber', description='Both yell ‘COO-EE’ loudly 3 times facing up.', points=10),
        Task(name='Social Butterfly', description='Talk to a group of 3+ strangers for 3 minutes.', points=30),
        Task(name='Serious Business', description='Give ridiculous but serious life advice to a stranger. They must acknowledge it.', points=20),
        Task(name='Mannequin Challenge', description='Freeze in a weird pose in a crowded area for 1 minute.', points=30),
        Task(name='Speedy Slider', description='Go down 3 different slides in 5 minutes.', points=10),
        Task(name='Words of Wisdom', description='Ask 3 strangers for inspirational quotes; they must oblige.', points=20),
        Task(name='Speedy Gonzalez', description='Race a member of the public. You must win.', points=20),
        Task(name='But I’m Tired…', description='Lie down and pretend to sleep for 3 minutes. Eyes closed entire time.', points=20),
        Task(name='For the Gram', description='Take a selfie with a stranger with their permission.', points=30),
        Task(name='Expert Reporter', description='Interview a stranger on an obscure topic. They must answer for atleast 30s.', points=30),
        Task(name='Like and Subscribe', description='Get a stranger to subscribe to Remy’s Movies (@remysmovies7740)', points=40),
        Task(name='David Attenborough', description='Photograph a turtle and eel in one photo.', points=20),
        Task(name='New Heights', description='Climb at least 3m of a 5m+ tree.', points=10),
        Task(name='Nerd Alert', description=r'Do the shown homework (no phone/calculator). Score 75%+ in 15 mins.', points=30),
        Task(name='Broadcasting Live', description='Send current location on group chat.', points=40),
        Task(name='Iron Core', description='Plank for 2m 30s without body touching ground (except hands/feet).', points=30),
        Task(name='Movie Fanatic', description='Recreate a famous movie scene (30s+) in a public place.', points=10),
        Task(name='#1 Swiftie', description='Perform a full Taylor Swift song (2+ mins) in a public area.', points=20),
        Task(name='The Floor is Lava', description='You must cross a distance of at least 15m without any part of you or clothing attached to you touching the ground.', points=30),
        Task(name='King of the Hill', description='Stand at the highest point of Sydney park for 2 mins without crouching or hiding between obstacles.', points=30),
        Task(name='Tourism', description='You must touch 4 different identifiable landmarks in Sydney Park (e.g. smokestacks, skate park edge, cafe, major signs).', points=20),
        Task(name='One Leg Wonder', description='Both partners may stand on 1 foot for 1 min without any other body part or article of clothing touching anything but your partner.', points=10),
        Task(name='Meet the Parents', description='You must find and stay with Remy’s parents for at least 1 min. (They get lonely)', points=20),
    ]

    for task in tasks_to_add:
        if task.name not in existing_tasks:
            db.session.add(task)

    db.session.commit()
    print("Tasks added to database.")
