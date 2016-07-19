from flask.ext.script import Manager

from connector.handlers import create_app

manager = Manager(create_app)

if __name__ == '__main__':
    pass
