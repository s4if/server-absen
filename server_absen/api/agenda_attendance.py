from flask import Blueprint, request, jsonify, g
from ..models import AgendaTemplateAttendance, User, AgendaTemplate, db
from ..utils import protected
import datetime
from geopy.distance import geodesic
import pytz

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

ag_bp = Blueprint('agenda_template_attendance', __name__, url_prefix='/agenda')

@ag_bp.route('/attendance', methods=['POST'])
@protected
def log_agenda_template_attendance():
    data = request.get_json()
    required_fields = {'agenda_template_id', 'attendance_datetime', 'latitude', 'longitude'}
    if not data or not required_fields.issubset(data.keys()):
        return jsonify({'message': 'Ada data yang kurang'}), 400

    try:
        attendance_datetime = datetime.datetime.fromisoformat(data['attendance_datetime']).astimezone(JAKARTA_TZ)
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

    agenda_template = AgendaTemplate.query.filter_by(id=data['agenda_template_id']).first()
    if not agenda_template:
        return jsonify({'message': 'Agenda template tidak ditemukan'}), 404

    # Check for duplicate attendance within 30 minutes
    # Need Manual Check
    start_time = attendance_datetime - datetime.timedelta(minutes=30)
    prev_attendance = AgendaTemplateAttendance.query.filter(
        AgendaTemplateAttendance.user_id == user.id,
        AgendaTemplateAttendance.agenda_template_id == agenda_template.id,
        AgendaTemplateAttendance.attendance_datetime >= start_time,
        AgendaTemplateAttendance.attendance_datetime <= attendance_datetime
    ).order_by(AgendaTemplateAttendance.attendance_datetime.desc()).first()
    if prev_attendance:
        distance = geodesic(
            (prev_attendance.latitude, prev_attendance.longitude), 
            (latitude, longitude)
        ).meters
        if distance < 50:
            return jsonify({'message': 'Kehadiran sudah ada untuk agenda ini dalam 30 menit terakhir'}), 400

    attendance = AgendaTemplateAttendance(
        agenda_template_id=agenda_template.id,
        user_id=user.id,
        attendance_datetime=attendance_datetime,
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(attendance)
    db.session.commit()

    return jsonify({'message': 'Kehadiran berhasil dicatat'}), 201

@ag_bp.route('/attendance', methods=['GET'])
@protected
def get_agenda_template_attendance():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    attendances = AgendaTemplateAttendance.query.filter_by(user_id=user.id).order_by(AgendaTemplateAttendance.attendance_datetime.desc()).all()
    data = [{
        'id': a.id,
        'agenda_template_id': a.agenda_template_id,
        'attendance_datetime': a.attendance_datetime.isoformat(),
        'latitude': a.latitude,
        'longitude': a.longitude
    } for a in attendances]

    return jsonify({'data': data}), 200

@ag_bp.route('/attendance/<int:id>', methods=['GET'])
@protected
def get_agenda_template_attendance_by_id(id):
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    attendance = AgendaTemplateAttendance.query.filter_by(id=id, user_id=user.id).first()
    if not attendance:
        return jsonify({'message': 'Data kehadiran tidak ditemukan'}), 404

    data = {
        'id': attendance.id,
        'agenda_template_id': attendance.agenda_template_id,
        'attendance_datetime': attendance.attendance_datetime.isoformat(),
        'latitude': attendance.latitude,
        'longitude': attendance.longitude
    }

    return jsonify({'data': data}), 200

@ag_bp.route('/attendance', methods=['DELETE'])
@protected
def delete_agenda_template_attendance():
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({'message': 'Ada data yang kurang'}), 400

    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404

    attendance = AgendaTemplateAttendance.query.filter_by(id=data['id'], user_id=user.id).first()
    if not attendance:
        return jsonify({'message': 'Data kehadiran tidak ditemukan'}), 404

    db.session.delete(attendance)
    db.session.commit()

    return jsonify({'message': 'Kehadiran berhasil dihapus'}), 200

@ag_bp.route('/list_agenda', methods=['GET'])
@protected
def get_agenda_template_list():
    user = User.query.filter_by(username=g.user_data['username']).first()
    if not user:
        return jsonify({'message': 'Pengguna tidak ditemukan'}), 404
    
    # nanti lebih kompleks lagi.. bwahahaha
    result = db.session.query(db.Text(
        """
        SELECT at.*
        FROM agenda_templates at
        JOIN agenda_template_divisions atd ON at.id = atd.agenda_template_id
        WHERE atd.division_id = :division_id;
    """
    )).params(division_id=user.division_id)
    data = result.fetchall()
    return jsonify({'data': data}), 200