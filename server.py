import os
from flask import Flask, abort, request, jsonify, g, url_for
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from datetime import datetime
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

# Create the application instance
app = Flask(__name__, template_folder="templates")
app.config.from_object(Config)


db = SQLAlchemy(app)


# Models
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=60000000):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data['id'])
        return user

    def __repr__(self):
        return '<User {}>'.format(self.username)


class ProcessedSong(db.Model):
    __tablename__ = 'processed_songs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    create_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=backref('user', uselist=False))
    rating = db.Column(db.Float, nullable=True)
    genre = db.Column(db.String(64))
    is_public = db.Column(db.Boolean)
    is_processed = db.Column(db.Boolean)
    file_path = db.Column(db.String(256), unique=True)
    external_id = db.Column(db.Integer, unique=True)


db.create_all()


# LOGIN METHODS

def is_token_valid(token):
    user = User.verify_auth_token(token)
    if not user:
        return False
    g.user = user
    return True


def json_error(error_message):
    return jsonify({"message": error_message})

# ROUTES
@app.route('/api/users', methods=['POST'])
def register_user():
    username = request.json.get('username')
    password = request.json.get('password')
    email = request.json.get('email')

    if username is None or password is None:
        return json_error("Неправильный логин или пароль"), 500

    if email is None:
        return

    if User.query.filter_by(username=username).first() is not None:
        return json_error("Пользователь с таким именем уже существует"), 500

    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    print('user id: ', user.id)
    token = user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})


@app.route('/api/login', methods=['POST'])
def login_user():
    username = request.json.get('username')
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if not user:
        return json_error("Пользователя не существует"), 400

    if not user.verify_password(password):
        return json_error("Неверный пароль"), 400

    token = user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})


@app.route('/api/genres', methods=['GET'])
def get_genres():
    genres = []
    for filename in os.listdir('models'):
        path = os.path.join('models', filename)
        if os.path.isfile(path):
            if "DS" not in filename:
                genres.append(filename[:-3])
    return jsonify(genres)


@app.route('/api/songs/process', methods=['POST'])
def process_song():
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    song_name = request.json.get('name')
    genre = request.json.get('genre')
    user_id = g.user.id

    song = ProcessedSong(name=song_name)
    song.genre = genre
    song.user_id = user_id
    song.is_processed = False
    song.is_public = False


@app.route('/api/songs', methods=['GET'])
def get_songs():
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    songs = ProcessedSong.query.filter_by(user_id=g.user.id)

    return jsonify(songs)


@app.route('/api/songs/<id>', methods=['GET'])
def send_song_file():
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    song = ProcessedSong.load(id)
    if song is None:
        abort(404)
    url = song.file_path
    return jsonify({"url": url})


@app.route('/')
def home():
    return "Test"


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run()