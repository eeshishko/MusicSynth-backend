from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery


def make_celery(flask_app):
    print("CELERY_URL: ", flask_app.config['CELERY_RESULT_BACKEND'])
    celery = Celery(
        app.import_name,
        backend=flask_app.config['CELERY_RESULT_BACKEND'],
        broker=flask_app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(flask_app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Create the application instance
app = Flask(__name__)
app.config.from_object(Config)

celery = make_celery(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import models, routes

db.create_all()

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run()
