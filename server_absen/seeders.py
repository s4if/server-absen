import random
from datetime import datetime, timedelta
from .models import (
    db, Admin, User, AttendanceLocation, Attendance, Division, GenderType, AttendanceStatusType,
    AgendaTemplate, AgendaTemplateDivision, SelfReportedAttendance
)

def seed_all():
    """Seed all tables with initial data"""
    seed_admin()
    seed_divisions()
    seed_users()
    seed_attendance_locations()
    seed_attendances()
    seed_agenda_templates()
    seed_self_reported_attendances()
    db.session.commit()

def seed_admin():
    """Seed admin table with initial admin user"""
    if Admin.query.filter_by(username='admin').first() is None:
        admin = Admin(
            username='admin',
            full_name='Administrator'
        )
        admin.set_password('admin123')  # You should change this in production
        db.session.add(admin)

def seed_divisions():
    """Seed divisions table with sample divisions"""
    sample_divisions = [
        {
            'name': 'SMAIT',
            'full_name': 'SMAIT Ihsanul Fikri',
            'description': 'Sekolah Menengah Atas Islam Terpadu'
        },
        {
            'name': 'SMPTI',
            'full_name': 'SMPIT Ihsanul FIkri',
            'description': 'Sekolah Menengah Pertama Terpadu Islam'
        },
        {
            'name': 'Kebersihan',
            'full_name': 'Divisi Kebersihan',
            'description': 'Divisi Kebersihan'
        }
    ]

    for division_data in sample_divisions:
        if Division.query.filter_by(name=division_data['name']).first() is None:
            division = Division(
                name=division_data['name'],
                full_name=division_data['full_name'],
                description=division_data['description']
            )
            db.session.add(division)

def seed_users():
    """Seed users table with sample users"""
    sample_users = [
        {
            'username': 'mrfu',
            'password': 'password123',
            'division_name': 'SMAIT',
            'gender': GenderType.MALE,
            'full_name': 'Ahmad Fuad, S.Pd.'
        },
        {
            'username': 'ismail',
            'password': 'password123',
            'division_name': 'SMKIT',
            'gender': GenderType.MALE,
            'full_name': 'Ismail, S.T.'
        },
        {
            'username': 'pamelri',
            'password': 'password123',
            'division_name': 'SMPTI',
            'gender': GenderType.MALE,
            'full_name': 'Pamel Riyadi, S.Pd.'
        }
    ]

    for user_data in sample_users:
        if User.query.filter_by(username=user_data['username']).first() is None:
            division = Division.query.filter_by(name=user_data['division_name']).first()
            if not division:
                continue  # Skip if the division does not exist

            user = User(
                username=user_data['username'],
                division_id=division.id,
                full_name=user_data['full_name'],
                gender=user_data['gender']
            )
            user.set_password(user_data['password'])
            db.session.add(user)

def seed_attendance_locations():
    """Seed attendance_locations table with sample locations"""
    sample_locations = [
        {
            'id': '1',
            'name': 'SMAIT Ihsanul Fikri',
            'short_name': 'SMAIT1',
            'latitude': '-7.583571594340874',
            'longitude': '110.25037258950822',
            'description': 'depan TU SMAIT',
          },
          {
            'id': '2',
            'name': 'SMPIT Ihsanul Fikri',
            'short_name': 'SMPIT1',
            'latitude': '-7.584018928602248',
            'longitude': '110.25155007925902',
            'description': 'depan TU Akhwat SMPIT',
          },
          {
            'id': '3',
            'name': 'SMKIT Ihsanul Fikri',
            'short_name': 'SMKIT1',
            'latitude': '-7.5684832452628825',
            'longitude': '110.2397089624626',
            'description': 'depan TU SMKIT',
          },
    ]

    for location_data in sample_locations:
        if AttendanceLocation.query.filter_by(id=location_data['id']).first() is None:
            location = AttendanceLocation(
                id=int(location_data['id']),
                name=location_data['name'],
                short_name=location_data['short_name'],
                latitude=float(location_data['latitude']),
                longitude=float(location_data['longitude']),
                description=location_data['description']
            )
            db.session.add(location)

def seed_attendances():
    """Seed attendances table with sample attendance records"""
    import pytz
    jakarta_tz = pytz.timezone('Asia/Jakarta')

    # Get a user for sample attendance
    user = User.query.filter_by(username='mrfu').first()
    if not user:
        return

    # Get a location for sample attendance
    location = AttendanceLocation.query.filter_by(id='1').first()
    if not location:
        return

    # Create attendance for the last 5 days
    for i in range(5):
        date = datetime.now(jakarta_tz) - timedelta(days=i)
        attendance_date = date.date()
        
        # Skip if attendance already exists for this date
        if Attendance.query.filter_by(user_id=user.id, attendance_date=attendance_date).first():
            continue

        # Create check-in time at 07:30 in Asia/Jakarta timezone
        check_in_time = date.replace(hour=7, minute=30, second=0, microsecond=0)
        
        # Create check-out time at 16:00 in Asia/Jakarta timezone
        check_out_time = date.replace(hour=16, minute=0, second=0, microsecond=0)

        attendance = Attendance(
            user_id=user.id,
            attendance_date=attendance_date,
            check_in=check_in_time,
            check_in_location_id=location.id,
            check_out=check_out_time,
            check_out_location_id=location.id,
            status=AttendanceStatusType.PRESENT,
            notes='Regular attendance'
        )
        db.session.add(attendance)
        
def seed_agenda_templates():
    """Seed agenda_templates and agenda_template_divisions with sample data"""
    import pytz
    from datetime import time

    # Sample agenda templates
    sample_templates = [
        {
            'name': 'Apel Pagi SMAIT',
            'description': 'Apel pagi rutin untuk SMAIT',
            'type': 'routine',
            'status': 'active',
            'start_time': time(7, 0),
            'end_time': time(7, 30),
            'frequency': 1,
            'division_names': ['SMAIT'],
            'location_name': 'SMAIT Ihsanul Fikri',
            'latitude': -7.58357159,
            'longitude': 110.25037259,
        },
        {
            'name': 'Apel Pagi SMPTI',
            'description': 'Apel pagi rutin untuk SMPTI',
            'type': 'routine',
            'status': 'active',
            'start_time': time(7, 0),
            'end_time': time(7, 30),
            'frequency': 1,
            'division_names': ['SMPTI'],
            'location_name': 'SMPIT Ihsanul Fikri',
            'latitude': -7.58401892,
            'longitude': 110.25155008,
        },
        {
            'name': 'Rapat Divisi Kebersihan',
            'description': 'Rapat mingguan divisi kebersihan',
            'type': 'flexible-routine',
            'status': 'active',
            'start_time': time(13, 0),
            'end_time': time(14, 0),
            'frequency': 7,
            'division_names': ['Kebersihan'],
            'location_name': 'SMKIT Ihsanul Fikri',
            'latitude': -7.56848324,
            'longitude': 110.23970896,
        }
    ]

    jakarta_tz = pytz.timezone('Asia/Jakarta')

    for tmpl in sample_templates:
        # Check if template already exists by name
        if AgendaTemplate.query.filter_by(name=tmpl['name']).first() is not None:
            continue

        # Get division objects
        divisions = []
        for div_name in tmpl['division_names']:
            div = Division.query.filter_by(name=div_name).first()
            if div:
                divisions.append(div)
        if not divisions:
            continue  # Skip if no valid division

        agenda_template = AgendaTemplate(
            name=tmpl['name'],
            description=tmpl['description'],
            type=tmpl['type'],
            status=tmpl['status'],
            start_time=tmpl['start_time'],
            end_time=tmpl['end_time'],
            frequency=tmpl['frequency'],
            location_name=tmpl['location_name'],
            latitude=tmpl['latitude'],
            longitude=tmpl['longitude'],
            created_at=datetime.now(jakarta_tz),
            updated_at=datetime.now(jakarta_tz)
        )
        agenda_template.divisions = divisions
        db.session.add(agenda_template)


def seed_self_reported_attendances():
    """Seed self_reported_attendances table with sample data"""
    import pytz
    from datetime import datetime, timedelta

    jakarta_tz = pytz.timezone('Asia/Jakarta')
    users = User.query.all()
    if not users:
        return  # No users to create self-reported attendances for

    sample_agenda_names = ['Meeting', 'Training', 'Workshop', 'Seminar']
    sample_location_names = ['Conference Room', 'Training Room', 'Main Hall', 'Auditorium']

    for user in users:
        # Create 5 self-reported attendances for each user
        for i in range(5):
            attendance_time = datetime.now(jakarta_tz) - timedelta(days=i)
            self_reported_attendance = SelfReportedAttendance(
                user_id=user.id,
                attendance_time=attendance_time,
                agenda_name=f"{random.choice(sample_agenda_names)} {i+1}",
                location_name=random.choice(sample_location_names),
                address=f"Address {i+1}",
                latitude=-7.5 + (i * 0.1),
                longitude=110.2 + (i * 0.1)
            )
            db.session.add(self_reported_attendance)