from flask import Flask

from connector import youtube, facebook


def create_app():
    app = Flask(__name__)
    app.register_blueprint(youtube)
    app.register_blueprint(facebook)
    return app

