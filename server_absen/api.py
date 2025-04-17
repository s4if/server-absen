from flask import Blueprint, request, jsonify, g, current_app
from .models import SelfReportedAttendance
from functools import wraps
import jwt
import datetime
from .models import AttendanceLocation, User, Attendance, db
import pytz
from geopy.distance import geodesic

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
            return jsonify({'message': 'Header otorisasi tidak ada'}), 401
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Format token tidak valid'}), 401

        try:
            data = jwt.decode(parts[1], current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user_data = data
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token kedaluwarsa'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid'}), 401

    return wrapper

@bp.route('/login', methods=['POST'])
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

@bp.route('/self_reported_attendance', methods=['POST'])
@protected
def log_self_reported_attendance():
    data = request.get_json()
    required_fields = {'agenda_name', 'location_name', 'address', 'attendance_time', 'longitude', 'latitude'}
    if not data or not required_fields.issubset(data.keys()):
        return jsonify({'message': 'Ada data yang kurang'}), 400

    # Parse attendance_time
    try:
        attendance_time = datetime.datetime.fromisoformat(data['attendance_time']).astimezone(JAKARTA_TZ)
    except (ValueError, TypeError):
        return jsonify({'message': 'Invalid attendance_time format'}), 400

    # Validate coordinates
    try:
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
    except (ValueError, TypeError):
        return jsonify({'message': 'Format lintang atau bujur tidak valid'}), 400
    

    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return jsonify({'message': 'Lintang atau bujur di luar rentang yang valid'}), 400

    # Check if the user exists
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404
    
    # Calculate the 30-minute window start time
    start_time = attendance_time - datetime.timedelta(minutes=30)

    prev_self_report = SelfReportedAttendance.query.filter(
        SelfReportedAttendance.user_id == user.id,
        SelfReportedAttendance.attendance_time >= start_time,
        SelfReportedAttendance.attendance_time <= attendance_time
    ).order_by(SelfReportedAttendance.attendance_time.desc()).first()
    if prev_self_report:
        distance = geodesic(
            (prev_self_report.latitude, prev_self_report.longitude), 
            (latitude, longitude)
            ).meters
        if distance < 50:
            return jsonify({'message': 'Self-reported attendance already exists for this location under 30 minutes ago'}), 400

    self_report = SelfReportedAttendance(
        user_id=user.id,
        attendance_time=attendance_time,
        agenda_name=data['agenda_name'],
        location_name=data['location_name'],
        address=data.get('address'),
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(self_report)
    db.session.commit()

    return jsonify({'message': 'Kehadiran mandiri berhasil dicatat'}), 201

'''
Example Request
```json
POST /api/self_reported_attendance HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token>

{
    "agenda_name": "Project Meeting",
    "location_name": "Office Conference Room",
    "address": "Jl. Sudirman No. 123",
    "attendance_time": "2025-04-13T08:30:00+07:00",
    "latitude": -6.1958,
    "longitude": 106.8196
}
'''

@bp.route('/get_self_reported_attendance', methods=['GET'])
@protected
def get_self_reported_attendance():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    self_reports = SelfReportedAttendance.query.filter_by(user_id=user.id).all()
    data = [{
        'id': sr.id,
        'attendance_time': sr.attendance_time.isoformat(),
        'agenda_name': sr.agenda_name,
        'location_name': sr.location_name,
        'address': sr.address,
        'latitude': sr.latitude,
        'longitude': sr.longitude
    } for sr in self_reports]

    return jsonify(data), 200

@bp.route('/delete_self_reported_attendance', methods=['DELETE'])
@protected
def delete_self_reported_attendance():
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({'message': 'Ada data yang kurang'}), 400

    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    self_report = SelfReportedAttendance.query.filter_by(id=data['id'], user_id=user.id).first()
    if not self_report:
        return jsonify({'message': 'Data kehadiran mandiri tidak ditemukan'}), 404

    db.session.delete(self_report)
    db.session.commit()

    return jsonify({'message': 'Kehadiran mandiri berhasil dihapus'}), 200

@bp.route('/edit_self_reported_attendance', methods=['PUT'])
@protected
def edit_self_reported_attendance():
    data = request.get_json()
    required_fields = {'id', 'agenda_name', 'location_name', 'address'}
    if not data or not required_fields.issubset(data.keys()):
        return jsonify({'message': 'Ada data yang kurang'}), 400

    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    self_report = SelfReportedAttendance.query.filter_by(id=data['id'], user_id=user.id).first()
    if not self_report:
        return jsonify({'message': 'Self-reported attendance not found'}), 404

    # User can only update ageda name, location_name and address
    self_report.agenda_name = data['agenda_name']
    self_report.location_name = data['location_name']
    self_report.address = data.get('address')
    db.session.commit()

    return jsonify({'message': 'Kehadiran mandiri berhasil diperbarui'}), 200