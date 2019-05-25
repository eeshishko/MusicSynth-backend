import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'myverysecretlooooooooooongkey'
    TEMP_UPLOAD_URL = './temp'
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET', 'music-synth-backend')
    CELERY_BROKER_URL = os.environ.get('REDISCLOUD_URL') or 'redis://localhost:6379'
    CELERY_RESULT_BACKEND = os.environ.get('REDISCLOUD_URL') or 'redis://localhost:6379'
