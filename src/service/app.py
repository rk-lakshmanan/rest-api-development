#!/usr/bin/python

import json
import os
import uuid
import bcrypt
from flask_cors import CORS
from flask import Flask, jsonify
from flask import render_template
from flask import request
from flask_sqlalchemy import SQLAlchemy, sqlalchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import exc
from sqlalchemy.sql import func
from marshmallow import Schema, fields, pre_load, validate
import datetime
import dateutil.parser


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
    password = db.Column(db.String(60), unique=False, nullable=False)
    token = db.Column(db.String(36), unique=False, nullable=True)

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
        return str(uuid.uuid4())


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


class Diary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    publish_date = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    public = db.Column(db.Boolean, nullable=False)
    text = db.Column(db.Text, nullable=False)

    def __init__(self, title, author, public, text, publish_date):
        self.title = title
        self.author = author
        self.public = public
        self.text = text
        self.publish_date = publish_date

    def as_dict(self):
        return {c.name: unicode(getattr(self, c.name)) for c in self.__table__.columns}


class DiarySchema(ma.Schema):
    id = fields.Integer()
    title = fields.String(required=True, validate=[
        validate.Length(min=1, max=255, error="Title must have between {min} and {max} characters.")
    ])
    author = fields.String(required=True, validate=[
        validate.Length(min=1, max=255, error="Author must have between {min} and {max} characters.")
    ])
    public = fields.Boolean(required=True)
    text = fields.String(required=True, validate=[
        validate.Length(min=1, error="Text cannot be empty")
    ])

    class Meta:
        # Fields to expose
        fields = ('id', 'title', 'author', 'publish_date', 'public', 'text')


class InsertDiarySchema(ma.Schema):
    title = fields.String(required=True, validate=[
        validate.Length(min=1, max=255, error="Title must have between {min} and {max} characters.")
    ])
    public = fields.Boolean(required=True)
    text = fields.String(required=True, validate=[
        validate.Length(min=1, error="Text cannot be empty")
    ])
    token = fields.String(required=True, validate=[
        validate.Length(min=36, error="Text cannot be empty")
    ])

    class Meta:
        # Fields to expose
        fields = ('id', 'title', 'author', 'publish_date', 'public', 'text', 'token')


user_schema = UserSchema()
users_schema = UserSchema(many=True)
diary_schema = DiarySchema()
diaries_schema = DiarySchema(many=True)
insert_diary_schema = InsertDiarySchema()


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
@app.route("/users", methods=["POST"])
def get_user():
    if 'token' not in request.form.keys():
        return make_json_response("Invalid authentication token.", False)

    token_string = request.form['token']
    user = User.query.filter_by(token=token_string).first()

    if user is None:
        return make_json_response("Invalid authentication token.", False)

    user_info = {"username": user.username, "fullname": user.fullname, "age": user.age}
    return make_json_response(user_info, True, 200, None, True)


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


# endpoint to authenticate user
@app.route("/users/authenticate", methods=["POST"])
def user_authenticate():

    if 'username' not in request.form.keys() and 'password' not in request.form.keys():
        return make_json_response(None, False)
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if not user or not user.verify_password(password):
        return make_json_response(None, False)

    token_string = user.generate_auth_token()
    user.token = token_string
    db.session.commit()

    return make_json_response(token_string, True, 200, "token")


# endpoint to expire user token
@app.route("/users/expire", methods=["POST"])
def user_expire():

    if 'token' not in request.form.keys():
        return make_json_response(None, False)

    token_string = request.form['token']

    user = User.query.filter_by(token=token_string).first()

    if not user:
        return make_json_response(None, False)

    token_string = user.generate_auth_token()
    user.token = token_string
    db.session.commit()

    return make_json_response(None, True)


# endpoint to show all diaries
@app.route("/diary", methods=["GET"])
def get_all_diary():
    all_diaries = Diary.query.filter_by(public=True).all()
    result = diaries_schema.dump(all_diaries)
    return make_json_response(result.data)


# endpoint to delete user
@app.route("/diary", methods=["POST"])
def get_user_diary():
    if 'token' not in request.form.keys():
        return make_json_response("Invalid authentication token.", False)

    user = User.query.filter_by(token=request.form['token']).first()

    if user is None:
        return make_json_response("Invalid authentication token.", False)

    diaries = Diary.query.filter_by(author=user.fullname).all()
    result = diaries_schema.dump(diaries)

    return make_json_response(result[0], True)


def getDateTimeFromISO8601String(s):
    d = dateutil.parser.parse(s)
    return d


# endpoint to create diary
@app.route("/diary/create", methods=["POST"])
def add_diary():
    # Validate and deserialize input
    data, errors = insert_diary_schema.load(request.form)
    if errors:
        return make_json_response(errors, False)

    user = User.query.filter_by(token=data['token']).first()

    if user is None:
        return make_json_response("Invalid authentication token.", False)

    author = user.fullname
    publish_date = datetime.datetime.now().replace(microsecond=0).isoformat()
    publish_date = getDateTimeFromISO8601String(publish_date)

    new_diary = Diary(data['title'], author, data['public'], data['text'], publish_date)

    db.session.add(new_diary)

    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError as err:
        db.session.rollback()
        return make_json_response(err, False, 200)

    return make_json_response(new_diary.id, True, 201)


# endpoint to delete diary
@app.route("/diary/delete", methods=["POST"])
def delete_diary():
    if 'token' not in request.form.keys():
        return make_json_response("Invalid authentication token.", False)

    if 'id' not in request.form.keys():
        return make_json_response("Missing parameters.", False)

    user = User.query.filter_by(token=request.form['token']).first()

    if user is None:
        return make_json_response("Invalid authentication token.", False)

    diary = Diary.query.get(request.form['id'])

    if diary is None:
        return make_json_response("Invalid diary ID.", False)

    db.session.delete(diary)
    db.session.commit()

    return make_json_response(None, True)


# endpoint to adjust diary permission
@app.route("/diary/permission", methods=["POST"])
def update_diary_permission():
    if 'token' not in request.form.keys():
        return make_json_response("Invalid authentication token.", False)

    if 'id' not in request.form.keys() or 'private' not in request.form.keys():
        return make_json_response("Missing parameters.", False)

    user = User.query.filter_by(token=request.form['token']).first()

    if user is None:
        return make_json_response("Invalid authentication token.", False)

    if request.form['private'] == 'true' or request.form['private'] == True:
        permission = True
    else:
        permission = False

    diary = Diary.query.get(request.form['id'])

    if diary is None:
        return make_json_response("Invalid diary ID.", False)

    diary.public = permission
    db.session.commit()

    return make_json_response(None)


# Remember to update this list
ENDPOINT_LIST = ['/', '/meta/heartbeat', '/meta/members', '/users/register',
                 '/users/authenticate', '/users/expire', '/users', '/diary',
                 '/diary/create', '/diary/delete', '/diary/permission']


def make_json_response(data, status=True, code=200, key=None, raw=False):
    """Utility function to create the JSON responses."""

    to_serialize = {}
    if status:
        if data is not None:
            if raw:
                to_serialize = data
            else:
                if key is not None:
                    to_serialize[key] = data
                else:
                    to_serialize['result'] = data
        to_serialize['status'] = True
    else:
        if data is not None:
            if raw:
                to_serialize = data
            else:
                if key is not None:
                    to_serialize[key] = data
                else:
                    to_serialize['error'] = data
        to_serialize['status'] = False
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
