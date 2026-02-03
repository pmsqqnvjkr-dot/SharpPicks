from functools import wraps
from flask import Blueprint, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, current_user
from models import db, User

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function

login_manager = LoginManager()
auth_bp = Blueprint('auth', __name__)

def init_login_manager(app):
    login_manager.init_app(app)
    login_manager.login_view = None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({
        'id': user.id,
        'email': user.email,
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
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    login_user(user)
    return jsonify({
        'id': user.id,
        'email': user.email,
        'is_premium': user.is_premium,
        'unit_size': user.unit_size
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

@auth_bp.route('/user', methods=['GET'])
def get_user():
    if current_user.is_authenticated:
        return jsonify({
            'id': current_user.id,
            'email': current_user.email,
            'is_premium': current_user.is_premium,
            'unit_size': current_user.unit_size
        })
    return jsonify(None)

@auth_bp.route('/upgrade', methods=['POST'])
def upgrade():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    current_user.is_premium = True
    db.session.commit()
    return jsonify({'is_premium': True})

@auth_bp.route('/unit-size', methods=['POST'])
def set_unit_size():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json()
    unit_size = data.get('unit_size', 100)
    current_user.unit_size = unit_size
    db.session.commit()
    return jsonify({'unit_size': unit_size})
