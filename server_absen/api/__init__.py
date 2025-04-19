from flask import Blueprint, request, jsonify, g, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ..utils import protected
import jwt
import datetime
from ..models import AttendanceLocation, User, Attendance, db
import pytz

from .self_reported_attendance import sra_bp

bp = Blueprint('api', __name__, url_prefix='/api')
bp.register_blueprint(sra_bp)

# Initialize Flask-Limiter with whitelist for reverse proxy IP
limiter = Limiter(
    key_func=get_remote_address,  # Use the client's IP address as the key
    default_limits=["100 per minute"],  # Default limit for all routes
    storage_uri="memory://"  # In-memory storage for simplicity; use Redis in production
)

# TODO: move to config.py
# Trusted reverse proxy IPs
TRUSTED_PROXY_IPS = {"127.0.0.1", "192.168.1.1"}

# Custom key function to extract the real client IP
def get_real_ip():
    # Check if the request comes through a trusted reverse proxy
    remote_addr = get_remote_address()
    if remote_addr in TRUSTED_PROXY_IPS:
        # Extract the original client IP from the X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # The first IP in the list is the original client IP
            return forwarded_for.split(",")[0].strip()
    # Fallback to the remote address if no trusted proxy is detected
    return remote_addr

# Set the custom key function for Flask-Limiter
limiter.key_func = get_real_ip

# Whitelist reverse proxy IPs
@limiter.request_filter
def whitelist_reverse_proxy():
    return get_remote_address() in TRUSTED_PROXY_IPS


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

@bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Limit to 5 requests per minute for login
def login():
    data = request.get_json()
    required_fields = {'username', 'password', 'device_id'}
    if not required_fields.issubset(data):
        return jsonify({'error': 'Kredensial tidak lengkap'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Kredensial tidak valid'}), 401

    token, refresh_time = generate_token(user, data['device_id'])
    if not token:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404
        
    return jsonify({'token': token, 'refresh_time': refresh_time}), 200

@bp.route('/refresh_token', methods=['GET'])
@protected
def refresh_token():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user or user.deleted_at:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    token, refresh_time = generate_token(user, g.user_data['device_id'])
    return jsonify({'token': token, 'refresh_time': refresh_time}), 200

@bp.route('/dashboard_data', methods=['GET'])
@protected
def dashboard_data():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404
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
        return jsonify({'message': 'Kolom yang diperlukan tidak ada'}), 400

    if data['device_id'] != g.user_data['device_id']:
        return jsonify({'message': 'ID perangkat tidak valid'}), 403

    if data['attendance_type'] not in {'check_in', 'check_out'}:
        return jsonify({'message': 'Jenis kehadiran tidak valid'}), 400

    att_loc = AttendanceLocation.query.get(data['location_id'])
    if not att_loc:
        return jsonify({'message': 'Lokasi tidak valid'}), 400

    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    now = datetime.datetime.now(JAKARTA_TZ)
    date = now.date()
    attendance = Attendance.query.filter_by(user_id=user.id, attendance_date=date).first()

    if data['attendance_type'] == 'check_in':
        if attendance:
            return jsonify({'message': 'Sudah check-in'}), 400
        attendance = Attendance(
            user_id=user.id,
            attendance_date=date,
            check_in=now,
            check_in_location_id=data['location_id']
        )
        db.session.add(attendance)
        db.session.commit()
        return jsonify({'message': 'Check-in berhasil'}), 200

    if not attendance:
        return jsonify({'message': 'Belum check-in'}), 400
        
    attendance.check_out = now
    attendance.check_out_location_id = data['location_id']
    db.session.commit()
    return jsonify({'message': 'Check-out berhasil'}), 200
