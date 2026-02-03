from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    is_premium = db.Column(db.Boolean, default=False)
    unit_size = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)
    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class TrackedBet(db.Model):
    __tablename__ = 'tracked_bets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey(User.id), nullable=False)
    pick = db.Column(db.String, nullable=False)
    game = db.Column(db.String, nullable=False)
    bet_amount = db.Column(db.Integer, nullable=False)
    odds = db.Column(db.Integer, default=-110)
    to_win = db.Column(db.Float)
    result = db.Column(db.String, nullable=True)
    profit = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship(User, backref='tracked_bets')
