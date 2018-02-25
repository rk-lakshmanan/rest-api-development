#!/usr/bin/python

from flask import Flask,render_template
from flask_cors import CORS
import json
import os

# app = Flask(__name__)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../html/templates')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../html/static/')

# ASSETS_DIR =  './html/'
# STATIC_DIR = './html/static/'
# print(ASSETS_DIR)
app = Flask(__name__, template_folder=ASSETS_DIR, static_folder=STATIC_DIR)
# Enable cross origin sharing for all endpoints
CORS(app)

# Remember to update this list
ENDPOINT_LIST = ['/', '/meta/heartbeat', '/meta/members']

def make_json_response(data, status=True, code=200):
    """Utility function to create the JSON responses."""

    to_serialize = {}
    if status:
        to_serialize['status'] = True
        if data is not None:
            to_serialize['result'] = data
    else:
        to_serialize['status'] = False
        to_serialize['error'] = data
    response = app.response_class(
        response=json.dumps(to_serialize),
        status=code,
        mimetype='application/json'
    )
    return response


@app.route("/")
def index():
    """Returns a list of implemented endpoints."""
    return make_json_response(ENDPOINT_LIST)
    # INDEX_PATH = os.path.join(ASSETS_DIR,'index.html')
    # print(INDEX_PATH)
    # print(os.path.isfile(INDEX_PATH))
    # # print(STATIC_DIR)
    # # print(ASSETS_DIR)
    # mypath = os.path.abspath(__file__)
    # print(mypath)
    # print(app.instance_path)
    # print()
    # print()

    # return render_template('index.html')


@app.route("/meta/heartbeat")
def meta_heartbeat():
    """Returns true"""
    return make_json_response(None)


@app.route("/meta/members")
def meta_members():
    """Returns a list of team members"""
    with open("./team_members.txt") as f:
        team_members = f.read().strip().split("\n")
    return make_json_response(team_members)


if __name__ == '__main__':
    # Change the working directory to the script directory
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    # Run the application
    app.run(debug=False, port=8080, host="0.0.0.0")
