import os
from flask import abort, request, jsonify, g, flash
from app import app, db
from app.models import User, ProcessedSong, is_token_valid
from ml_models.model_processing import proc
from werkzeug.utils import secure_filename

ALLOWED_SONG_EXTENSIONS = {'mid'}


def json_error(error_message):
    return jsonify({"message": error_message})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_SONG_EXTENSIONS


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

    if 'song' not in request.files:
        flash('No file part')
        return json_error("Не удалось загрузить файл на сервер"), 500

    file = request.files['song']
    temp_dir = app.config['TEMP_UPLOAD_URL']

    if file.filename == '':
        flash('No selected file')
        return json_error("Имя файла не должно быть пустым"), 500
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(temp_dir, filename))

    genre = request.args.get("genre")
    if not genre:
        return json_error("Необходимо указать жанр"), 500

    if ProcessedSong.query.filter_by(name=file.filename, user_id=g.user.id).first() is not None:
        return json_error("Мелодия с таким названием уже имеется у вас библиотеке"), 500

    song = ProcessedSong(name=file.filename)
    song.genre = genre
    song.user_id = g.user.id
    song.is_processed = False
    song.is_public = False
    db.session.add(song)
    db.session.commit()

    # TODO: поставить эту таску в background
    # proc(temp_dir + '/' + file.filename)

    return jsonify(song.serialize)


@app.route('/api/songs', methods=['GET'])
def get_songs():
    """
        Возвращает список песен под авторизованным юзером
        :return: Array<ProcessedSong>
        """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    songs = ProcessedSong.query.filter_by(user_id=g.user.id)

    return jsonify([i.serialize for i in songs.all()])


@app.route('/api/songs/<song_id>', methods=['GET'])
def send_song_file(song_id):
    """
    Скачивание обработанной мелодии по id этой мелодии
    :return: TODO
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    song = ProcessedSong.load(song_id)
    if song is None:
        abort(404)
    url = song.file_path
    return jsonify({"url": url}) # TODO:


@app.route('/api/songs/public', methods=['GET'])
def get_public_songs():
    """
    Возвращает список песен, которые были помечены юзерами как доступные всем. Все трэки также должны быть уже
    обработаны.
    :return: Array<ProcessedSong>
    """
    songs = ProcessedSong.query.filter_by(is_public=True, is_processed=True)
    return jsonify([i.serialize for i in songs.all()])


@app.route('/api/songs/<song_id>/rate', methods=['POST'])
def rate_songs(song_id):
    """
    Выставляет рейтинг от авторизованного пользователя заданной песни
    :param song_id:
    """


@app.route('/api/songs/<song_id>/makePublic', methods=['POST'])
def make_song_public(song_id):
    """
    Делает пользовательскую мелодии доступную в общем пуле мелодий.
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    song = ProcessedSong.query.filter_by(id=song_id, user_id=g.user.id).first()
    if song is None:
        return json_error("Такой песни не существует"), 500

    song.is_public = True
    db.session.add(song)
    db.session.commit()
    return jsonify({}), 200


@app.route('/')
def home():
    return "Test"
