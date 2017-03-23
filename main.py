import jsonpickle
from aiohttp import web
import socketio

import database

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

@sio.on('connect')
def connect(sid, environ):
    print("joined")
    sio.enter_room(sid, "scout")

@sio.on('submit_match')
async def submit_match(sid, data):
    database.submit_match(data)

    await sio.emit('submit_match', data, room="scout", skip_sid=sid)

@sio.on('submit_team')
async def submit_team(sid, data):
    database.submit_team(data)

    await sio.emit('submit_team', data, room="scout", skip_sid=sid)

@sio.on('request_update')
async def request_update(sid, data):
    update = database.request_update(data)
    for doc in update:
        event = ""
        if isinstance(doc, database.Teams): 
            event = "submit_team"
        elif isinstance(doc, database.Matches):
            event = "submit_match"

        dic = doc.to_mongo().to_dict()
        dic.pop('_id')
        raw = jsonpickle.encode(dic, unpicklable=False)
        await sio.emit(event, raw, room=sid)

@sio.on('disconnect')
def disconnect(sid):
    print("left")
    sio.leave_room(sid, "scout")

if __name__ == '__main__':
    web.run_app(app)
