import os

from flask import Blueprint
from pymongo import MongoClient

from config import ASSET_MONGO_DB
from config import CONNECTOR_MONGO_DB

APP_ROOT = os.path.dirname(os.path.abspath(__file__)).replace(os.sep + 'connector', '')


api = Blueprint('api', __name__)


def mongo_connection_url(system):
    if system == 'internal':
        return CONNECTOR_MONGO_DB if 'CONNECTOR_MONGO_DB' not in os.environ else os.environ['CONNECTOR_MONGO_DB']
    return ASSET_MONGO_DB if 'ASSET_MONGO_DB' not in os.environ else os.environ['ASSET_MONGO_DB']


internal_client = MongoClient(mongo_connection_url('internal'))
external_client = MongoClient(mongo_connection_url('external'))


