from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import JSONB
import uuid
import random
import string

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)


def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=4))
    return f"SHARP-{suffix}"


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String, unique=True, nullable=False)
    username = db.Column(db.String, nullable=True)
    display_name = db.Column(db.String, nullable=True)
    password_hash = db.Column(db.String, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    founding_member = db.Column(db.Boolean, default=False)
    founding_number = db.Column(db.Integer, nullable=True)
    subscription_status = db.Column(db.String, default='free')
    subscription_plan = db.Column(db.String, nullable=True)
    trial_start_date = db.Column(db.DateTime, nullable=True)
    trial_end_date = db.Column(db.DateTime, nullable=True)
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    stripe_customer_id = db.Column(db.String, nullable=True)
    referral_code = db.Column(db.String, unique=True, default=generate_referral_code)
    referred_by = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    notification_prefs = db.Column(JSONB, default=lambda: {
        'pick_alert': True,
        'no_action': False,
        'outcome': True,
        'weekly_summary': True
    })
    is_premium = db.Column(db.Boolean, default=False)
    is_superuser = db.Column(db.Boolean, default=False)
    unit_size = db.Column(db.Integer, default=100)
    trial_ends = db.Column(db.DateTime, nullable=True)
    trial_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_pro(self):
        if self.is_superuser:
            return True
        if self.subscription_status in ('active', 'trial'):
            return True
        if self.trial_end_date and self.trial_end_date > datetime.now():
            return True
        return False


class Pick(db.Model):
    __tablename__ = 'picks'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    published_at = db.Column(db.DateTime, default=datetime.now)
    sport = db.Column(db.String, default='nba')
    away_team = db.Column(db.String, nullable=False)
    home_team = db.Column(db.String, nullable=False)
    game_date = db.Column(db.String, nullable=False)
    side = db.Column(db.String, nullable=False)
    line = db.Column(db.Float, default=0)
    line_open = db.Column(db.Float, nullable=True)
    line_close = db.Column(db.Float, nullable=True)
    start_time = db.Column(db.String, nullable=True)
    edge_pct = db.Column(db.Float, nullable=False)
    model_confidence = db.Column(db.Float, nullable=False)
    predicted_margin = db.Column(db.Float, nullable=True)
    sigma = db.Column(db.Float, nullable=True)
    z_score = db.Column(db.Float, nullable=True)
    raw_edge = db.Column(db.Float, nullable=True)
    cover_prob = db.Column(db.Float, nullable=True)
    implied_prob = db.Column(db.Float, nullable=True)
    market_odds = db.Column(db.Integer, default=-110)
    sportsbook = db.Column(db.String, default='DraftKings')
    closing_spread = db.Column(db.Float, nullable=True)
    clv = db.Column(db.Float, nullable=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    result = db.Column(db.String, default='pending')
    result_ats = db.Column(db.String, nullable=True)
    result_resolved_at = db.Column(db.DateTime, nullable=True)
    pnl = db.Column(db.Float, nullable=True)
    profit_units = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String, nullable=True)


class Pass(db.Model):
    __tablename__ = 'passes'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = db.Column(db.String, nullable=False)
    sport = db.Column(db.String, default='nba')
    games_analyzed = db.Column(db.Integer, default=0)
    closest_edge_pct = db.Column(db.Float, default=0)
    pass_reason = db.Column(db.String, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    model_run_id = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class ModelRun(db.Model):
    __tablename__ = 'model_runs'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = db.Column(db.String, nullable=False)
    sport = db.Column(db.String, default='nba')
    games_analyzed = db.Column(db.Integer, default=0)
    pick_generated = db.Column(db.Boolean, default=False)
    pick_id = db.Column(db.String, db.ForeignKey('picks.id'), nullable=True)
    pass_id = db.Column(db.String, db.ForeignKey('passes.id'), nullable=True)
    run_duration_ms = db.Column(db.Integer, default=0)
    model_version = db.Column(db.String, default='v1.0')
    created_at = db.Column(db.DateTime, default=datetime.now)


class UserBet(db.Model):
    __tablename__ = 'user_bets'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    pick_id = db.Column(db.String, db.ForeignKey('picks.id'), nullable=False)
    wager_amount = db.Column(db.Float, nullable=False)
    tracked_at = db.Column(db.DateTime, default=datetime.now)
    user_notes = db.Column(db.String, nullable=True)
    user = db.relationship('User', backref='user_bets')
    pick = db.relationship('Pick', backref='user_bets')


class Referral(db.Model):
    __tablename__ = 'referrals'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    referred_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    code_used = db.Column(db.String, nullable=False)
    days_credited = db.Column(db.Integer, default=14)
    created_at = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String, default='pending')
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_made')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referrals_received')


class FoundingCounter(db.Model):
    __tablename__ = 'founding_counter'
    id = db.Column(db.Integer, primary_key=True, default=1)
    current_count = db.Column(db.Integer, default=0)
    last_updated_at = db.Column(db.DateTime, default=datetime.now)
    closed = db.Column(db.Boolean, default=False)


class TrackedBet(db.Model):
    __tablename__ = 'tracked_bets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    pick_id = db.Column(db.String, db.ForeignKey('picks.id'), nullable=True)
    pick = db.Column(db.String, nullable=False)
    game = db.Column(db.String, nullable=False)
    bet_amount = db.Column(db.Integer, nullable=False)
    odds = db.Column(db.Integer, default=-110)
    to_win = db.Column(db.Float)
    result = db.Column(db.String, nullable=True)
    profit = db.Column(db.Float, default=0)
    source = db.Column(db.String, default='sharp_pick')
    follow_type = db.Column(db.String, default='exact')
    line_at_bet = db.Column(db.Float, nullable=True)
    odds_at_publish = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user = db.relationship('User', backref='tracked_bets', overlaps="user_bets")
    linked_pick = db.relationship('Pick', backref='tracked_bets')


class Insight(db.Model):
    __tablename__ = 'insights'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String, nullable=False)
    slug = db.Column(db.String, unique=True, nullable=False)
    category = db.Column(db.String, nullable=False)
    excerpt = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String, default='draft')
    publish_date = db.Column(db.DateTime, nullable=True)
    featured = db.Column(db.Boolean, default=False)
    pass_day = db.Column(db.Boolean, default=False)
    reading_time_minutes = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
