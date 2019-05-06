from flask import (
    Flask
)
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from datetime import datetime

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
    password_hash = db.Column(db.String(128), nullable=True)

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

# Create a URL route in our application for "/"
@app.route('/')
def home():
    """
    This function just responds to the browser ULR
    localhost:5000/

    :return:        the rendered template 'home.html'
    """
    return "Hello world!"

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run(debug=True)