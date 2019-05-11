from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Create the application instance
app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import models, routes

db.create_all()

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run()
