from flask import Blueprint, request, jsonify, g
from ..models import SelfReportedAttendance, User, db
from ..utils import protected
import datetime
from geopy.distance import geodesic
import pytz

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

self_reported_attendance_bp = Blueprint('self_reported_attendance', __name__, url_prefix='/self_reported')


@self_reported_attendance_bp.route('/attendance', methods=['POST'])
@protected
def log_self_reported_attendance():
    data = request.get_json()
    required_fields = {'agenda_name', 'location_name', 'address', 'attendance_time', 'longitude', 'latitude'}
    if not data or not required_fields.issubset(data.keys()):
        return jsonify({'message': 'Ada data yang kurang'}), 400

    try:
        attendance_time = datetime.datetime.fromisoformat(data['attendance_time']).astimezone(JAKARTA_TZ)
    except (ValueError, TypeError):
        return jsonify({'message': 'Format waktu salah'}), 400

    try:
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
    except (ValueError, TypeError):
        return jsonify({'message': 'Format lintang atau bujur tidak valid'}), 400

    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return jsonify({'message': 'Lintang atau bujur di luar rentang yang valid'}), 400

    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

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
            return jsonify({'message': 'Kehadiran mandiri sudah ada untuk lokasi ini dalam 30 menit terakhir'}), 400

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

@self_reported_attendance_bp.route('/attendance', methods=['GET'])
@protected
def get_self_reported_attendance():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    self_reports = SelfReportedAttendance.query.filter_by(user_id=user.id).order_by(SelfReportedAttendance.attendance_time.desc()).all()
    data = [{
        'id': sr.id,
        'attendance_time': sr.attendance_time.isoformat(),
        'agenda_name': sr.agenda_name,
        'location_name': sr.location_name,
        'address': sr.address,
        'latitude': sr.latitude,
        'longitude': sr.longitude
    } for sr in self_reports]

    return jsonify({'data': data}), 200

@self_reported_attendance_bp.route('/attendance/<int:id>', methods=['GET'])
@protected
def get_self_reported_attendance_by_id(id):
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    self_report = SelfReportedAttendance.query.filter_by(id=id, user_id=user.id).first()
    if not self_report:
        return jsonify({'message': 'Data kehadiran mandiri tidak ditemukan'}), 404

    data = {
        'id': self_report.id,
        'attendance_time': self_report.attendance_time.isoformat(),
        'agenda_name': self_report.agenda_name,
        'location_name': self_report.location_name,
        'address': self_report.address,
        'latitude': self_report.latitude,
        'longitude': self_report.longitude
    }

    return jsonify({'data': data}), 200

@self_reported_attendance_bp.route('/attendance', methods=['DELETE'])
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

@self_reported_attendance_bp.route('/attendance', methods=['PUT'])
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
        return jsonify({'message': 'Kehadiran mandiri tidak ditemukan'}), 404

    self_report.agenda_name = data['agenda_name']
    self_report.location_name = data['location_name']
    self_report.address = data.get('address')
    db.session.commit()

    return jsonify({'message': 'Kehadiran mandiri berhasil diperbarui'}), 200