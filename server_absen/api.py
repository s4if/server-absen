from flask import Blueprint, request, jsonify, g, current_app
from functools import wraps
import jwt
import datetime
from .models import AttendanceLocation, User, Attendance, db
import pytz

bp = Blueprint('api', __name__, url_prefix='/api')

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

def generate_token(user, device_id) -> tuple:
    if user.deleted_at is not None:
        return None, None

    today = datetime.datetime.now(JAKARTA_TZ).date()
    user.last_login = today
    db.session.commit()

    now = datetime.datetime.now(JAKARTA_TZ)
    exp = now + datetime.timedelta(minutes=30)
    token_payload = {
        'username': user.username,
        'device_id': device_id,
        'exp': exp
    }
    token = jwt.encode(
        token_payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    refresh_at = now + datetime.timedelta(hours=12)
    return token, refresh_at.isoformat()

def protected(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Authorization header missing'}), 401
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Invalid token format'}), 401

        try:
            data = jwt.decode(parts[1], current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user_data = data
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

    return wrapper

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    required_fields = {'username', 'password', 'device_id'}
    if not required_fields.issubset(data):
        return jsonify({'error': 'Missing credentials'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    token, refresh_time = generate_token(user, data['device_id'])
    if not token:
        return jsonify({'message': 'User not found'}), 404
        
    return jsonify({'token': token, 'refresh_time': refresh_time}), 200

@bp.route('/refresh_token', methods=['GET'])
@protected
def refresh_token():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user or user.deleted_at:
        return jsonify({'message': 'User not found'}), 404

    token, refresh_time = generate_token(user, g.user_data['device_id'])
    return jsonify({'token': token, 'refresh_time': refresh_time}), 200

@bp.route('/dashboard_data', methods=['GET'])
@protected
def dashboard_data():
    user = User.query.filter_by(username=g.user_data['username']).first()
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
    locations = AttendanceLocation.query.filter_by(deleted_at=None).all()
    return jsonify([{
        'id': loc.id,
        'name': loc.name,
        'short_name': loc.short_name,
        'latitude': loc.latitude,
        'longitude': loc.longitude
    } for loc in locations])

@bp.route('/daily_attendance', methods=['POST'])
@protected
def daily_attendance():
    # needed fields: location_id, attendance_type (check_in or check_out), device_id

    data = request.get_json()

    if not data or 'location_id' not in data or 'attendance_type' not in data or 'device_id' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    if data['device_id'] != g.user_data['device_id']:
        return jsonify({'message': 'Invalid device ID'}), 403

    if data['attendance_type'] not in {'check_in', 'check_out'}:
        return jsonify({'message': 'Invalid attendance type'}), 400

    att_loc = AttendanceLocation.query.get(data['location_id'])
    if not att_loc:
        return jsonify({'message': 'Invalid location'}), 400

    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    now = datetime.datetime.now(JAKARTA_TZ)
    date = now.date()
    attendance = Attendance.query.filter_by(user_id=user.id, attendance_date=date).first()

    if data['attendance_type'] == 'check_in':
        if attendance:
            return jsonify({'message': 'Already checked in'}), 400
        attendance = Attendance(
            user_id=user.id,
            attendance_date=date,
            check_in=now,
            check_in_location_id=data['location_id']
        )
        db.session.add(attendance)
        db.session.commit()
        return jsonify({'message': 'Check in successful'}), 200

    if not attendance:
        return jsonify({'message': 'Not checked in yet'}), 400
        
    attendance.check_out = now
    attendance.check_out_location_id = data['location_id']
    db.session.commit()
    return jsonify({'message': 'Check out successful'}), 200