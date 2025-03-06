from flask import Blueprint, request, jsonify, g, current_app
from functools import wraps
import jwt
import datetime
from .model import AttendanceLocation, User

bp = Blueprint('api', __name__, url_prefix='/api')

# Add your API routes here
# Decorator to protect routes
def protected(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Authorization header is missing'}), 401

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({'message': 'Invalid Authorization header'}), 401

        token = parts[1]
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user_data = data  # Store decoded token data in g
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
    return wrapper

# Login endpoint
@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400

    username = data['username']
    password = data['password']

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        # Ensure token is a string (handles PyJWT 1.x and 2.x compatibility)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

@bp.route('/refresh_token', methods=['POST'])
@protected
def refresh_token():
    # Get the current user from the token
    username = g.user_data['user']
    
    # Generate a new token
    new_token = jwt.encode({
        'user': username,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    # Ensure new_token is a string
    if isinstance(new_token, bytes):
        new_token = new_token.decode('utf-8')
    
    return jsonify({'token': new_token})

# Protected dashboard data endpoint
@bp.route('/dashboard_data', methods=['GET'])
@protected
def dashboard_data():
    username = g.user_data['user']
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({
        'message': f'Welcome {user.full_name}',
        'role': user.role
    })

@bp.route('/cek_login', methods=['GET'])
@protected
def cek_login():
    return jsonify({'message': 'logged_in'})

@bp.route('/get_permitted_locations', methods=['GET'])
@protected
def get_permitted_locations():
    locations = AttendanceLocation.query.all()
    data = [
        {
            'id': location.id,
            'name': location.name,
            'short_name': location.short_name,
            'latitude': location.latitude,
            'longitude': location.longitude
        } for location in locations
    ]
    return jsonify(data)