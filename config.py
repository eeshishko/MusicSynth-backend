import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://127.0.0.1/music-synth'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'myverysecretlooooooooooongkey'