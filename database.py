import time

from mongoengine import *

# Connect to recon MongoDB Database
connect('recon')

# MongoDB Collection + Sub-collections
class Auton(EmbeddedDocument):
    passed_baseline = BooleanField(required=True)
    placed_gear = BooleanField(required=True)
    shot_ball = BooleanField(required=True)

class Teleop(EmbeddedDocument):
    high = BooleanField(required=True)
    low = BooleanField(required=True)
    gears_on_ship = IntField(required=True)
    hoppers_activated = IntField(required=True)
    balls_in_boiler = IntField(required=True)

class Endgame(EmbeddedDocument):
    climber = BooleanField(required=True)
    fouls = IntField(required=True)
    score = IntField(required=True)

class Matches(Document):
    date = IntField(default=int(time.time() * 1000))
    team = IntField(required=True, max_length=4)
    match = IntField(required=True, max_length=3)
    color = StringField(required=True)

    # Implemented/Embedded Documents
    auton = EmbeddedDocumentField(Auton)
    teleop = EmbeddedDocumentField(Teleop)
    end = EmbeddedDocumentField(Endgame)

def submit_match(match):
    m = Matches.from_json(match)

    query = Q(team=m.team) & Q(match=m.match)
    Matches.objects(query).delete()

    m.save(force_insert=True)

class Teams(Document):
    date = IntField(default=int(time.time() * 1000))
    number = IntField(require=True, max_length=4)

def submit_team(team):
    t = Teams.from_json(team)
    Teams.objects(number=t.number).delete()
    t.save(force_insert=True)

def request_update(date):
    query = Q(date__gt = date)

    docs = []
    docs.extend(Matches.objects(query))
    docs.extend(Teams.objects(query))

    return docs
