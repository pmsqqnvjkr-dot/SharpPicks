from functools import wraps
from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from email_validator import validate_email, EmailNotValidError
from models import db, User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()
login_manager = LoginManager()

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    username = data.get('username', email.split('@')[0])
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    try:
        valid = validate_email(email)
        email = valid.normalized
    except EmailNotValidError:
        return jsonify({'error': 'Please enter a valid email address'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 400
    
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User()
    user.email = email
    user.username = username
    user.password_hash = hashed
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'is_premium': user.is_premium,
        'unit_size': user.unit_size
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if user and user.password_hash and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'is_premium': user.is_premium,
            'unit_size': user.unit_size
        })
    
    return jsonify({'error': 'Invalid email or password'}), 401

@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    if request.method == 'GET':
        return redirect('/')
    return jsonify({'message': 'Logged out'})

@auth_bp.route('/user', methods=['GET'])
def get_user():
    if current_user.is_authenticated:
        return jsonify({
            'id': current_user.id,
            'email': current_user.email,
            'username': getattr(current_user, 'username', current_user.email.split('@')[0]),
            'is_premium': current_user.is_premium,
            'unit_size': current_user.unit_size
        })
    return jsonify(None)

@auth_bp.route('/upgrade', methods=['POST'])
@require_login
def upgrade():
    current_user.is_premium = True
    db.session.commit()
    return jsonify({'is_premium': True})

@auth_bp.route('/unit-size', methods=['POST'])
@require_login
def set_unit_size():
    data = request.get_json()
    unit_size = data.get('unit_size', 100)
    current_user.unit_size = unit_size
    db.session.commit()
    return jsonify({'unit_size': unit_size})
