import os

import mysql.connector

from dotenv import load_dotenv  # reads the .env file
from flask import Flask, render_template

from . import stay


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    app.register_blueprint(stay.bp)

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.errorhandler(404)
    def not_found(err):
        return render_template(
            "error.html", code=404, message="The requested page could not be found"
        ), 404

    @app.errorhandler(400)
    def bad_request(err):
        return render_template("error.html", code=400, message=err.description), 400

    @app.errorhandler(405)
    def method_not_allowed(err):
        return render_template(
            "error.html",
            code=405,
            message="This page only works with a button, not by typing the address.",
        ), 405

    @app.errorhandler(mysql.connector.Error)
    def database_error(err):
        app.logger.error("database error %s", err.errno)
        return render_template(
            "error.html",
            code=500,
            message="Something went wrong with the database. Please try again later.",
        ), 500

    return app
