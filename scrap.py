from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from mongoengine import *

import time, json, jsonpickle

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

# Analyze Calculations
class AnalyzePacket:
    def __init__(self, action, team, opr, ccwm, avgpts, avggears, avghops, avgfouls):
        self.action = action
        self.team = team
        self.opr = opr
        self.ccwm = ccwm
        self.avgpts = avgpts
        self.avggears = avggears
        self.avghops = avghops
        self.avgfouls = avgfouls

clients = []

class Recon(WebSocket):
    def handleConnected(self):
        clients.append(self)
        print self.address, 'connected'

    def handleClose(self):
        clients.remove(self)
        print self.address, 'disconnected'

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

            matchArray = []
            matchArray.append(SubmitData('new_match', match.to_mongo().to_dict()))

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
            cpacket = ConfirmationPacket(SubmitData('match', {'match': data['form']['match'], 'team': data['form']['team']}))
            craw = jsonpickle.encode(cpacket, unpicklable=False)
            self.sendMessage(unicode(craw))

            # Sends all clients new match received by server
            rpacket = RefreshPacket(matchArray)
            rraw = jsonpickle.encode(rpacket, unpicklable=False)

            for c in clients:
                if c != self:
                    c.sendMessage(unicode(rraw))

            # Calculates Analytical Data as Match is Submitted and sends it back to client
            played, alliance, oppositeAlliance, points, gears, hoppers, fouls = [], [], [], [], [], [], []

            for match in Matches.objects(team = data['form']['team']):
                played.append(match)
                alliance.append(match.end.score)
                points.append(match.end.score)
                gears.append(match.teleop.gears_on_ship)
                hoppers.append(match.teleop.hoppers_activated)
                fouls.append(match.end.fouls)

                for ally in Matches.objects(Q(match = played[0].match) & Q(color = played[0].color) & Q(team__ne = played[0].team)):
                    alliance.append(ally.end.score)

                for opponent in Matches.objects(Q(match = played[0].match) & Q(color__ne = played[0].color)):
                    oppositeAlliance.append(opponent.end.score)

            opposite = sum(oppositeAlliance)
            opr = sum(alliance)
            ccwm = sum(alliance) - sum(oppositeAlliance)
            avgpts = sum(points) / len(played)
            avggears = sum(gears) / len(played)
            avghops = sum(hoppers) / len(played)
            avgfouls = sum(fouls) / len(played)

            apacket = AnalyzePacket('new_analyze', data['team'], opr, ccwm, avgpts, avggears, avghops, avgfouls)
            araw = jsonpickle.encode(apacket, unpicklable=False)
            self.sendMessage(unicode(araw))

server = SimpleWebSocketServer('0.0.0.0', 8000, Recon)
server.serveforever()
