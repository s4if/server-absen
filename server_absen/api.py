from flask import Blueprint, request, jsonify, g, current_app
from functools import wraps
import jwt # from PyJWT!
import datetime
from .models import AttendanceLocation, User, Attendance
import pytz

bp = Blueprint('api', __name__, url_prefix='/api')
# TODO: API diberi rate limit

def generate_token(username, device_id) -> str:
    user = User.query.filter_by(username=username).first()

    if not user or user.deleted_at is not None:
        return jsonify({'message': 'User not found'}), 404
    
    last_login = datetime.datetime.now(pytz.timezone('Asia/Jakarta')).date()
    user.last_login = last_login
    current_app.db.session.commit()

    token = jwt.encode({
        'username': username,
        'device_id': device_id,
        'exp': datetime.datetime.now(pytz.timezone('Asia/Jakarta')) + datetime.timedelta(days=1)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    # Ensure token is a string (handles PyJWT 1.x and 2.x compatibility)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    refresh_at = datetime.datetime.now(pytz.timezone('Asia/Jakarta')) + datetime.timedelta(hours=12)
    return token, refresh_at

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
            # untuk pertimbangan, username dicocokan ke device_id atau tidak.
            # kalau dicocokkan harus request ke database. plusnya lebih aman, minusnya lebih lambat.
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

    # Ensure username, password, and device_id are provided
    if not all(k in data for k in ('username', 'password', 'device_id')):
        return jsonify({'error': 'Missing credentials'}), 400

    username = data['username']
    password = data['password']
    device_id = data['device_id']

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        token, refresh_time = generate_token(username, device_id)
        return jsonify({'token': token, 'refresh_time':refresh_time}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@bp.route('/refresh_token', methods=['POST'])
@protected
def refresh_token():
    # Get the current user from the token
    username = g.user_data['user']
    device_id = g.user_data['device_id']
    
    # Generate a new token
    token, refresh_time = generate_token(username, device_id)
    return jsonify({'token': token, 'refresh_time':refresh_time}), 200

# Protected dashboard data endpoint
@bp.route('/dashboard_data', methods=['GET'])
@protected
def dashboard_data():
    username = g.user_data['username']
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({
        'message': f'Welcome {user.full_name}',
        'role': user.division
    })

@bp.route('/cek_login', methods=['GET'])
@protected
def cek_login():
    return jsonify({'message': 'logged_in'})

@bp.route('/get_permitted_locations', methods=['GET'])
@protected
def get_permitted_locations():
    locations = AttendanceLocation.query.filter(AttendanceLocation.deleted_at.is_(None)).all()
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

@bp.route('/daily_attendance', methods=['POST'])
@protected
def daily_attendance():
    # payload: location_id, attendance_type
    data = request.get_json()
    location_id = data.get('location_id')
    if not location_id:
        return jsonify({'message': 'location_id is required'}), 400
    
    att_loc = AttendanceLocation.query.get(location_id)
    if not att_loc:
        return jsonify({'message': 'Invalid location_id'}), 400
    
    username = g.user_data['username']
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    date = datetime.datetime.now(jakarta_tz).date()
    attendance = Attendance.query.filter_by(user_id=user.id, attendance_date=date).first()
    if not attendance:
        if data.get('attendance_type') == 'check_out':
            return jsonify({'message': 'Not yet checked in'}), 400
        
        attendance = Attendance(
            user_id=user.id,
            attendance_date=date,
            check_in=datetime.datetime.now(jakarta_tz),
            check_in_location_id=location_id
        )
        current_app.db.session.add(attendance)
        current_app.db.session.commit()
        return jsonify({'message': 'Check in success'}), 200
    
    else:
        if data.get('attendance_type') == 'check_in':
            return jsonify({'message': 'Already checked in'}), 400
        
        # check out bisa diperbarui tanpa cek
        attendance.check_out = datetime.datetime.now(jakarta_tz)
        attendance.check_out_location_id = location_id
        current_app.db.session.commit()
        return jsonify({'message': 'Check out success'}), 200