import os

from flask import Blueprint

APP_ROOT = os.path.dirname(os.path.abspath(__file__)).replace(os.sep + 'connector', '')


api = Blueprint('api', __name__)



