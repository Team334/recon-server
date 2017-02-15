from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from mongoengine import *

import time, json, jsonpickle

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

class Teams(Document):
    date = IntField(default=int(time.time() * 1000))
    number = IntField(require=True, max_length=4)

# Class for sending refresh packets back to app
class RefreshPacket:
    def __init__(self, data):
        self.action = 'refresh'
        self.date = int(time.time() * 1000)
        self.data = data
class ConfirmationPacket:
    def __init__(self, data):
        self.action = 'received'
        self.data = data

# Class for sending data back wrapped in action type
class SubmitData:
    def __init__(self, action, data):
        self.action = action
        self.data = data

class Recon(WebSocket):
    def handleMessage(self):
        data = json.loads(self.data)

        if data['action'] == 'refresh':
            last_update = 0
            if data['last_update'] != '':
                last_update = int(data['last_update'])

            l = []
            for ob in Matches.objects(date__gt = last_update):
                l.append(SubmitData('new_match', ob.to_mongo().to_dict()))

            for ob in Teams.objects(date__gt = last_update):
                l.append(SubmitData('new_team', ob.to_mongo().to_dict()))

            packet = RefreshPacket(l)
            raw = jsonpickle.encode(packet, unpicklable=False)
            self.sendMessage(unicode(raw))

        # Saves Websocket input from app into MongoDB
        if data['action'] == 'submit_team':
            team = Teams(number = data['form']['number'])
            team.save()

            # Sends app confirmation that team was received by server
            packet = ConfirmationPacket(SubmitData('team', {'team': data['form']['number'], 'date': (time.time() * 1000)}))
            raw = jsonpickle.encode(packet, unpicklable=False)
            self.sendMessage(unicode(raw))

        if data['action'] == 'submit_match':
            match = Matches(team = data['form']['team'], color = data['form']['color'], match = data['form']['match'])

            auton = Auton(passed_baseline = data['form']['auton']['passed_baseline'], placed_gear = data['form']['auton']['placed_gear'], shot_ball = data['form']['auton']['shot_ball'])
            match.auton = auton

            teleop = Teleop(high = data['form']['teleop']['high'], low = data['form']['teleop']['low'], gears_on_ship = data['form']['teleop']['gears_on_ship'], balls_in_boiler = data['form']['teleop']['balls_in_boiler'], hoppers_activated = data['form']['teleop']['hoppers_activated'])
            match.teleop = teleop

            endgame = Endgame(climber = data['form']['end']['climber'], fouls = data['form']['end']['fouls'], score = data['form']['end']['score'])
            match.end = endgame

            # Checks if match has already been submitted and updates it to the new information
            if Matches.objects(Q(match = data['form']['match']) & Q(team = data['form']['team'])):
                for ob in Matches.objects(Q(match = data['form']['match']) & Q(team = data['form']['team'])):
                    ob.update(set__date = time.time() * 1000)
                    ob.update(set__auton = auton)
                    ob.update(set__teleop = teleop)
                    ob.update(set__end = endgame)
            else:
                match.save()

            # Sends app confirmation that match was received by server
            packet = ConfirmationPacket(SubmitData('match', {'match': data['form']['match'], 'team': data['form']['team']}))
            raw = jsonpickle.encode(packet, unpicklable=False)
            self.sendMessage(unicode(raw))

    def handleConnected(self):
        print self.address, 'connected'

    def handleClose(self):
        print self.address, 'disconnected'

server = SimpleWebSocketServer('0.0.0.0', 8000, Recon)
server.serveforever()
