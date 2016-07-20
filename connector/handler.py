from flask import Flask

from connector import api
from connector.db import RegistryModel
from connector.states import Downloading


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api)
    return app


@api.route('/update/<string:registry_id>')
def update_request(registry_id):
    try:
        registry_model = RegistryModel.create_from_registry_id(registry_id)
        if registry_model.status == 'notified':
            Downloading.create_downloading_state(registry_model).run()
    except Exception:
        pass


@api.route('/unpublish/<string:registry_id>')
def unpublish_request(registry_id):
    pass


@api.route('/delete/<string:registry_id>')
def delete_request(registry_id):
    pass
