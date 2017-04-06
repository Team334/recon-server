import time
import decimal

from mongoengine import *
import numpy as np

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

    log = Matches.objects(team=m.team)
    Teams.objects(number=m.team).update(avg_points=log.average("end.score"),
                                        avg_gears=log.average("teleop.gears_on_ship"),
                                        avg_hoppers=log.average("teleop.hoppers_activated"),
                                        avg_fouls=log.average("end.fouls"))

    # Calculate OPR & CCWM after complete
    # match has been submitted
    count = Matches.objects(match=m.match).count()
    if count == 6:
        Analytics.analyze()

class Teams(Document):
    date = IntField(default=int(time.time() * 1000))
    number = IntField(require=True, max_length=4)

    opr = DecimalField(default=0, precision=2, rounding=decimal.ROUND_CEILING)
    ccwm = DecimalField(default=0, precision=2, rounding=decimal.ROUND_CEILING)
    avg_points = DecimalField(default=0, precision=2, rounding=decimal.ROUND_CEILING)
    avg_gears = DecimalField(default=0, precision=2, rounding=decimal.ROUND_CEILING)
    avg_hoppers = DecimalField(default=0, precision=2, rounding=decimal.ROUND_CEILING)
    avg_fouls = DecimalField(default=0, precision=2, rounding=decimal.ROUND_CEILING)

def submit_team(team):
    t = Teams.from_json(team)
    Teams.objects(number=t.number).delete()
    t.save(force_insert=True)

def request_update(date):
    query = Q(date__gt=date)

    docs = []
    docs.extend(Matches.objects(query))
    docs.extend(Teams.objects(query))

    return docs

def request_rankings():
    rankings = Teams.objects().order_by("avg_points")
    return rankings

def request_analytics(team):
    t = Teams.objects(number=team).only(
        'opr', 'ccwm', 'avg_points', 'avg_gears', 'avg_hoppers', 'avg_fouls')

    return t.first()

# OPR/CCWM algo referenced from https://www.thebluealliance.com/
class Analytics(object):
    @classmethod
    def analyze(cls):
        teams, mappings = cls.gen_mappings()
        m = cls.build_m(mappings)
        print(m)

        opr = cls.calc_stat(teams, mappings, m, "opr")
        ccwm = cls.calc_stat(teams, mappings, m, "ccwm")
        
        for team in teams:
            Teams.objects(number=team).update(opr=opr[team], ccwm=ccwm[team])

    @classmethod
    def calc_stat(cls, teams, mappings, M, typ):
        s = cls.build_s(mappings, typ)
        m_inv = np.linalg.pinv(M)

        x = np.dot(m_inv, s)

        stats = {}
        for team, stat in zip(teams, x):
            stats[team] = stat[0]
        return stats

    @classmethod
    def gen_mappings(cls):
        teams = set()
        for m in Matches.objects():
            teams.add(m.team)

        teams = list(teams)
        team_mappings = {}
        for i, t in enumerate(teams):
            team_mappings[t] = i

        return teams, team_mappings

    @classmethod
    def build_m(cls, mappings):
        n = len(mappings.keys())
        M = np.zeros([n, n])

        for m in Matches.objects():
            query = Q(color=m.color) & Q(match=m.match)
            alliance = Matches.objects(query)

            for ally in alliance:
                M[mappings[m.team], mappings[ally.team]] += 1

        return M

    @classmethod
    def build_s(cls, mappings, typ): 
        n = len(mappings.keys())
        s = np.zeros([n, 1])

        for m in Matches.objects():
            val = m.end.score
            if typ == "ccwm":
                opposing = "blue" if m.color == "red" else "red"
                query = Q(color=opposing) & Q(match=m.match)
                opp_score = Matches.objects(query).first().end.score
                val -= opp_score

            s[mappings[m.team]] = val

        return s
