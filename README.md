Recon Server
============
The backend server for the [Recon FRC 2017 scouting app](https://github.com/Team334/recon).

Usage
-----
Be sure to have [MongoDB](https://docs.mongodb.com/manual/installation/) and Python 3.x installed.
1. Download the repository:
```
$ git clone https://github.com/Team334/recon-server.git
$ cd recon-server/
```
2. Install the dependencies:
```
$ sudo pip3 install mongoengine jsonpickle python-socketio aiohttp aiodns numpy
```
3. Start MongoDB in the background:
```
$ sudo mongod
```
4. Start Recon Server:
```
$ python3 main.py
```
Recon Server is now ready to accept connections from the Recon client.
