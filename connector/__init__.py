import os

from flask import Flask

APP_ROOT = os.path.dirname(os.path.abspath(__file__)).replace(os.sep + 'connector', '')

app = Flask(__name__)
