from server import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(120), index=True)
    password_hash = db.Column(db.String(128), nullable=True)

    def __repr__(self):
        return '<User {}>'.format(self.username)


class ProcessedSong(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    create_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Float, nullable=True)
    genre = db.Column(db.String(64))
    is_public = db.Column(db.Boolean)
    is_processed = db.Column(db.Boolean)
    file_path = db.Column(db.String(256), unique=True)
    external_id = db.Column(db.Integer, unique=True)
