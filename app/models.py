from app import app, db
from flask import g
from datetime import datetime, tzinfo, timedelta
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from sqlalchemy.orm import backref


# Helpers methods

class simple_utc(tzinfo):
    def tzname(self,**kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def is_token_valid(token):
    user = User.verify_auth_token(token)
    if not user:
        return False
    g.user = user
    return True


# Models
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    create_date = db.Column(db.DateTime, index=True, default=datetime.now())
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
            return None
        except BadSignature:
            return None
        user = User.query.get(data['id'])
        return user

    def __repr__(self):
        return '<User {}>'.format(self.username)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }


class SongRating(db.Model):
    __tablename__ = 'song_rating'
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    rating = db.Column(db.Integer, nullable=False)


class SynthInfo(db.Model):
    __tablename__ = 'synth_info'
    id = db.Column(db.Integer, primary_key=True)
    raw_song_id = db.Column(db.Integer)
    song_id = db.Column(db.Integer)
    processing_complete = db.Column(db.Boolean, default=False)
    genre = db.Column(db.String(64))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'song_id': self.song_id,
            'raw_song_id': self.raw_song_id,
            'genre': self.genre,
            'is_processed': self.processing_complete
        }


class Song(db.Model):
    __tablename__ = 'song'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    create_date = db.Column(db.DateTime, index=True, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref=backref('user', uselist=False))
    is_public = db.Column(db.Boolean, default=False)
    synth_info_id = db.Column(db.Integer, db.ForeignKey('synth_info.id'), nullable=True)
    synth_info = db.relationship("SynthInfo", backref=backref('synth_info', uselist=False))

    @property
    def user_rating(self):
        user_rate = SongRating.query.filter_by(song_id=self.id, user_id=g.user.id).first()
        if user_rate is None:
            return None
        return user_rate.rating

    @property
    def average_rating(self):
        if SongRating.query.filter_by(song_id=self.id).first() is None:
            return None

        song_ratings = SongRating.query.filter_by(song_id=self.id).all()
        int_array = [i.rating for i in song_ratings]
        return sum(int_array) / float(len(int_array))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'create_date': self.create_date.replace(tzinfo=simple_utc()).isoformat(),
            'rating': self.average_rating,
            'user_rating': self.user_rating,
            'is_public': self.is_public,
            'user': self.user.serialize,
            'synth_info': None if self.synth_info is None else self.synth_info.serialize
        }

