from flask.ext.script import Manager, Server

from connector.handler import create_app

manager = Manager(create_app)

if __name__ == '__main__':
    manager.add_command("runserver", Server(host="0.0.0.0", port=5000))
    manager.run()
