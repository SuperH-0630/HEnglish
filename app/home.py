import flask.blueprints
import flask


home = flask.blueprints.Blueprint("home", __name__)


@home.route("/")
def index():
    return flask.render_template("index.html")
