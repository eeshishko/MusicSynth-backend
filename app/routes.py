import os
from flask import abort, request, jsonify, g
from app import app, db
from app.models import User, ProcessedSong, is_token_valid


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
    for filename in os.listdir('ml_models'):
        path = os.path.join('ml_models', filename)
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
