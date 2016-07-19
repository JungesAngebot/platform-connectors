from flask import Flask

from connector import youtube, facebook


def create_app():
    app = Flask(__name__)
    app.register_blueprint(youtube)
    app.register_blueprint(facebook)
    return app


@youtube.route('/upload/youtube/<string:category_id>/<string:video_id>')
def upload_video_to_youtube(category_id, video_id):
    pass


@youtube.route('/update/youtube/<string:category_id>/<string:video_id>')
def update_video_on_youtube(category_id, video_id):
    pass


@youtube.route('/unpublish/youtube/<string:category_id>/<string:video_id>')
def unpublish_video_on_youtube(category_id, video_id):
    pass
