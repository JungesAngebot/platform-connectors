from flask import Flask

from connector import api


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api)
    return app


@api.route('/update/<string:registry_id>')
def update_request(registry_id):
    pass


@api.route('/unpublish/<string:registry_id>')
def unpublish_request(registry_id):
    pass


@api.route('/delete/<string:registry_id>')
def delete_request(registry_id):
    pass
