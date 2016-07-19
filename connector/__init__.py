import os

from flask import Blueprint

APP_ROOT = os.path.dirname(os.path.abspath(__file__)).replace(os.sep + 'connector', '')


youtube = Blueprint('youtube', __name__)

facebook = Blueprint('facebook', __name__)

