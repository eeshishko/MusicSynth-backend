import os
from flask import abort, request, jsonify, g, flash, send_file
from app import app, db, celery, s3_resource
from app.models import User, Song, SongRating, SynthInfo, is_token_valid
from ml_models.model_processing import proc
from werkzeug.utils import secure_filename
import shutil
import time

ALLOWED_SONG_EXTENSIONS = {'mid'}


def json_error(error_message):
    return jsonify({"message": error_message})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_SONG_EXTENSIONS


@celery.task()
def process_midi_file(filename, genre, synth_info_id, user_id):
    temp_dir = app.config['TEMP_UPLOAD_URL']
    file_path = f'{temp_dir}/{filename}'
    print(os.listdir('.'))
    processed_file = proc(file_path, genre)
    with app.app_context():
        synth_info = SynthInfo.query.filter_by(id=synth_info_id).first()
        s3_resource.Object(app.config['S3_BUCKET_NAME'], str(user_id) + "/" + filename) \
            .upload_file(Filename=processed_file)
        synth_info.processing_complete = True
        db.session.add(synth_info)
        db.session.commit()
        # TODO: remove only user's file_path
        print(f'Processing of synthInfo {synth_info_id} is completed')


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
    user.email = email
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
    for filename in os.listdir('ml_models/models'):
        path = os.path.join('ml_models/models', filename)
        if os.path.isfile(path):
            if "DS" not in filename:
                genres.append(filename[:-3])
    return jsonify(genres)


@app.route('/api/songs/upload', methods=['POST'])
def upload_song():
    """
    Загружает песню на сервер, в базу данных и сохраняет файл на AWS
    :return:
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    if 'song' not in request.files:
        flash('No file part')
        return json_error("Не удалось загрузить файл на сервер"), 500

    temp_dir = app.config['TEMP_UPLOAD_URL']
    if os.path.isdir(temp_dir) is False:
        os.mkdir(temp_dir)

    file = request.files['song']
    if file.filename == '':
        flash('No selected file')
        return json_error("Имя файла не должно быть пустым"), 500

    existing_song = Song.query.filter_by(name=file.filename, user_id=g.user.id).first()
    if existing_song:
        return json_error("Мелодия с таким названием уже имеется у вас библиотеке"), 500

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(temp_dir, filename))

    file_path = str(g.user.id) + "/" + file.filename

    s3_resource.Object(app.config['S3_BUCKET_NAME'], file_path) \
        .upload_file(Filename=os.path.join(temp_dir, file.filename))

    song = Song(name=file.filename)
    song.user_id = g.user.id
    db.session.add(song)
    db.session.commit()
    return jsonify(song.serialize)


@app.route('/api/songs/process', methods=['POST'])
def process_song():
    """
    Загружает песню на сервер и отправляет ее на обработку
    :return:
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    genre = request.args.get("genre")
    if not genre:
        return json_error("Необходимо указать жанр"), 500

    if 'song' not in request.files:
        flash('No file part')
        return json_error("Не удалось загрузить файл на сервер"), 500

    temp_dir = app.config['TEMP_UPLOAD_URL']
    if os.path.isdir(temp_dir) is False:
        os.mkdir(temp_dir)

    file = request.files['song']
    if file.filename == '':
        flash('No selected file')
        return json_error("Имя файла не должно быть пустым"), 500

    existing_song = Song.query.filter_by(name=file.filename, user_id=g.user.id).first()
    if existing_song:
        return json_error("Мелодия с таким названием уже имеется у вас библиотеке"), 500

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(temp_dir, filename))

    song = Song(name=file.filename)
    song.user_id = g.user.id
    db.session.add(song)
    db.session.commit()

    synth_info = SynthInfo(song_id=song.id)
    synth_info.raw_song_id = request.args.get("raw_song_id")
    synth_info.genre = genre
    synth_info.processing_complete = False
    db.session.add(synth_info)
    db.session.commit()

    song.synth_info_id = synth_info.id
    db.session.commit()

    print("Before delay dir:")
    print(os.listdir('.'))
    process_midi_file.delay(file.filename, genre, synth_info.id, g.user.id)
    return jsonify(song.serialize)


@app.route('/api/songs', methods=['GET'])
def get_songs():
    """
        Возвращает список песен под авторизованным юзером
        :return: Array<Song>
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    songs = Song.query.filter_by(user_id=g.user.id)

    return jsonify([i.serialize for i in songs.all()])


@app.route('/api/songs/<song_id>', methods=['GET', 'DELETE'])
def download_song(song_id):
    """
    Скачивание мелодии по id этой мелодии
    :return: file from amazon
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    song = Song.query.filter_by(id=song_id).first()
    if song is None:
        return json_error("Мелодия с таким идентификатором не найдена")

    temp_dir = app.config['TEMP_UPLOAD_URL']
    if os.path.isdir(temp_dir) is False:
        os.mkdir(temp_dir)

    temp_file_path = f'{temp_dir}/{song.name}'

    s3_file_path = str(g.user.id) + "/" + song.name
    if request.method == 'GET':
        result = s3_resource.Object(app.config['S3_BUCKET_NAME'], s3_file_path)\
            .download_file(temp_file_path)
        return send_file(os.path.abspath(temp_file_path), as_attachment=True)

    if request.method == 'DELETE':
        s3_resource.Object(app.config['S3_BUCKET_NAME'], s3_file_path).delete()
        Song.query.filter_by(id=song_id).delete()
        db.session.commit()
        return jsonify({}), 200


@app.route('/api/public/songs', methods=['GET'])
def get_public_songs():
    """
    Возвращает список песен, которые были помечены юзерами как доступные всем
    :return: Array<Song>
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)
    songs = Song.query.filter_by(is_public=True)
    return jsonify([i.serialize for i in songs.all()])


@app.route('/api/songs/<song_id>/rate', methods=['POST'])
def rate_songs(song_id):
    """
    Выставляет рейтинг от авторизованного пользователя заданной песни
    :param song_id:
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)
    if not request.args.get("score"):
        return json_error("Рейтинг не задан")

    song_rating = SongRating.query.filter_by(song_id=song_id, user_id=g.user.id).first()

    if song_rating is None:
        song_rating = SongRating(song_id=song_id, user_id=g.user.id, rating=int(request.args.get("score")))
    else:
        song_rating.rating = request.args.get("score")

    db.session.add(song_rating)
    db.session.commit()

    song = Song.query.filter_by(id=song_id).first()

    return jsonify(song.serialize), 200


@app.route('/api/songs/<song_id>/makePublic', methods=['POST'])
def make_song_public(song_id):
    """
    Делает пользовательскую мелодии доступную в общем пуле мелодий.
    """
    if not is_token_valid(request.headers.get("Authorization")):
        return abort(401)

    song = Song.query.filter_by(id=song_id, user_id=g.user.id).first()
    if song is None:
        return json_error("Такой песни не существует"), 500

    song.is_public = True
    db.session.add(song)
    db.session.commit()
    return jsonify(song.serialize), 200


@app.route('/')
def home():
    return "Test"
