#!/usr/bin/python

from flask_cors import CORS
import json
import os
from flask import Flask, jsonify
from flask import render_template
from flask import request

from flask_sqlalchemy import SQLAlchemy, sqlalchemy
from flask_marshmallow import Marshmallow
from marshmallow import Schema, fields, pre_load, validate
import bcrypt
from sqlalchemy import exc
import uuid

app = Flask(__name__)
# Enable cross origin sharing for all endpoints
CORS(app)

#init app config
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)
ma = Marshmallow(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    fullname = db.Column(db.String(30), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(60), unique=False, nullable=False, primary_key=False)

    def __init__(self, username, password, fullname, age):
        self.username = username
        self.password = password
        self.fullname = fullname
        self.age = age

    def as_dict(self):
        return {c.name: unicode(getattr(self, c.name)) for c in self.__table__.columns}

    def verify_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    @staticmethod
    def generate_auth_token():
        return uuid.uuid4()


class UserSchema(ma.Schema):
    id = fields.Integer()
    username = fields.String(required=True, validate=[
        validate.Length(min=4, max=30, error="User name must have between {min} and {max} characters."),
        validate.Regexp(r"[a-zA-Z0-9_\-]*$",
                        error="User name must not contain special characters"
                              "(except _ und -)")
    ])
    password = fields.String(required=True, validate=[
        validate.Length(min=6, max=30, error="Password must have between {min} and {max} characters.")
    ])
    fullname = fields.String(required=True, validate=[
        validate.Length(min=1, error="Fullname cannot be empty")
    ])
    age = fields.Integer(required=True, validate=lambda n: n > 0)

    class Meta:
        # Fields to expose
        fields = ('id', 'username', 'fullname', 'age', 'password')


user_schema = UserSchema()
users_schema = UserSchema(many=True)


# endpoint to create new user
@app.route("/users/register", methods=["POST"])
def add_user():
    # Validate and deserialize input
    data, errors = user_schema.load(request.form)
    if errors:
        return make_json_response(errors)

    password_hash = bcrypt.hashpw(data['password'].encode("utf-8"), bcrypt.gensalt())
    new_user = User(data['username'], password_hash, data['fullname'], data['age'])

    db.session.add(new_user)

    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError as err:
        db.session.rollback()
        if "UNIQUE constraint failed: user.username" in str(err):
            return make_json_response("User already exists!", False, 200)
        else:
            return make_json_response("unknown error adding user", False, 200)

    return make_json_response(None, True, 201)


# endpoint to show all users
@app.route("/users", methods=["GET"])
def get_user():
    all_users = User.query.all()
    result = users_schema.dump(all_users)
    return make_json_response(result.data)


# endpoint to get user detail by id
@app.route("/users/<id>", methods=["GET"])
def user_detail(id):
    user = User.query.get(id)

    if user is None:
        return make_json_response("No result found.", False)

    return make_json_response(user.as_dict())


# endpoint to update user
@app.route("/users/<id>", methods=["PUT"])
def user_update(id):
    user = User.query.get(id)

    if user is None:
        return make_json_response("Invalid user id, no result found.", False)

    if 'username' not in request.form.keys() and 'password' not in request.form.keys():
        return make_json_response("Missing parameters.", False)

    username = request.form['username']
    password = request.form['password']
    password_hash = bcrypt.generate_password_hash(password)

    user.password = password_hash
    user.username = username

    db.session.commit()
    return make_json_response(user.as_dict())


# endpoint to delete user
@app.route("/users/<id>", methods=["DELETE"])
def user_delete(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()

    return make_json_response(user.as_dict())


# endpoint to delete user
@app.route("/users/authenticate", methods=["POST"])
def user_authenticate():

    if 'username' not in request.form.keys() and 'password' not in request.form.keys():
        return make_json_response("Missing parameters.", False)
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if not user or not user.verify_password(password):
        return make_json_response(None, False)

    token = {"token" : user.generate_auth_token()}
    return make_json_response(token, True)


# Remember to update this list
ENDPOINT_LIST = ['/', '/meta/heartbeat', '/meta/members', '/users']


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
    app.run(debug=True, port=8080, host="0.0.0.0")
