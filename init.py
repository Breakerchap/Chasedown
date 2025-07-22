import os
import sys
from app import app  # Import your Flask app
from app import db, User, Task

# ensure folders exist
base = os.path.dirname(__file__)
os.makedirs("/mnt/uploads", exist_ok=True)

def run():
    """Seed database; called from app.py or manually."""
    with app.app_context():  # <<<<<< CRITICAL
        db.create_all()
        with db.session.no_autoflush:  # safe bulk ops
            # create admin
            if not User.query.filter_by(username="admin").first():
                db.session.add(User(username="admin",
                                    password="lavender*123",
                                    role="admin", points=0))
                
            # replace tasks
            Task.query.delete()
            db.session.bulk_save_objects([    
                Task(name='Hunt the Hunters', description='Video the Hunters for 30s without getting tipped. They must always be on video and clearly visible.', points=40, time_limit=1200),
                Task(name='Out in the Open', description='Stand out in an open area for 2 mins with no blockages within 15m and only sparse bushland within 30m.', points=30, time_limit=1200),
                Task(name='Bush Survival 101', description='Build a bush shelter from scratch. Post picture on group chat.', points=40, time_limit=1800),
                Task(name='Just Dance', description='Do a full dance for at least 1.5 mins without moving from the spot.', points=30, time_limit=1200),
                Task(name='In Plain Sight', description='Stay in area with 5+ people within 30m for 5 minutes.', points=30, time_limit=600),
                Task(name='Pushup Prowess', description="Do atleast 25 pushups in 1 min. You chest much touch you partner's fist on the ground", points=30, time_limit=300),
                Task(name='The Way of the Pig', description='One partner must piggyback the other for 1.5 mins.', points=20, time_limit=300),
                Task(name='Moosuiance', description='Pretend to be a cow (moo & crawl) in a public area for 1 min.', points=10, time_limit=1200),
                Task(name='Echo Chamber', description='Both yell ‘COO-EE’ loudly 3 times facing up.', points=20, time_limit=1200),
                Task(name='Mannequin Challenge', description='Freeze in a weird pose in a crowded area for 1 minute.', points=10, time_limit=1200),
                Task(name='Speedy Slider', description='Go down 3 different slides 3 times per slide per partner.', points=10, time_limit=300),
                Task(name='But I’m Tired…', description='Lie down and pretend to sleep for 3 minutes. Eyes closed entire time.', points=20, time_limit=1200),
                Task(name='For the Gram', description='Take 5 photos of one partner in different areas and poses and caption them as if for instagram.', points=10, time_limit=1200),
                Task(name='Like and Subscribe', description='Watch a full video from Remy’s Movies (@remysmovies7740) and smash that like and subscribe button.', points=20, time_limit=600),
                Task(name='David Attenborough', description='Photograph a turtle and eel in one photo.', points=30, time_limit=1200),
                Task(name='New Heights', description='Climb at least 3m of a 5m+ tree.', points=10, time_limit=1200),
                Task(name='Broadcasting Live', description='Send live location on group chat for 5 mins.', points=20, time_limit=300),
                Task(name='Iron Core', description='Plank for 2 min without body touching ground (except hands/feet).', points=30, time_limit=600),
                Task(name='Movie Fanatic', description='Recreate a famous movie scene (30s+) in a public place.', points=10, time_limit=600),
                Task(name='#1 Swiftie', description='Perform a full Taylor Swift song (2+ mins) in a public area.', points=20, time_limit=1200),
                Task(name='The Floor is Lava', description='You must cross a distance of at least 15m without any part of you or worn clothing touching the ground.', points=30, time_limit=600),
                Task(name='King of the Hill', description='Stand at the highest point of Sydney park for 2 mins without crouching or hiding between obstacles.', points=30, time_limit=1200),
                Task(name='Tourism', description='You must touch 4 different identifiable landmarks in Sydney Park (e.g. smokestacks, skate park edge, cafe, major signs, ect.).', points=20, time_limit=1200),
                Task(name='One Leg Wonder', description='Both partners may stand on 1 foot for 1 min without leaning on any object or partner.', points=10, time_limit=300),
                Task(name='Meet the Parents', description='You must find and stay with Remy’s parents for at least 1 min. (They get lonely)', points=20, time_limit=1200),
                Task(name='MimeZone', description='You may not speak or make any verbal noises for 5mins.', points=20, time_limit=600),
                Task(name='Feng Shui Master', description='Balance 5 stones atop one another. They must stand for atleast 10s.', points=20, time_limit=600),
                Task(name='Gimme Five', description='High five another player, willingly or otherwise.', points=20, time_limit=1200),
                Task(name='Copycat', description="Both partners must mimic a stranger's movement from a distance for 1min.", points=20, time_limit=1200),
            ])

        db.session.commit()
        print("[init] Admin & tasks set up.")

if __name__ == "__main__":
    run()
