from datetime import datetime, timedelta
from .models import db, Admin, User, AttendanceLocation, Attendance, GenderType, AttendanceStatusType

def seed_all():
    """Seed all tables with initial data"""
    seed_admin()
    seed_users()
    seed_attendance_locations()
    seed_attendances()
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

def seed_users():
    """Seed users table with sample users"""
    sample_users = [
        {
            'username': 'mrfu',
            'password': 'password123',
            'division': 'SMA',
            'gender': GenderType.MALE,
            'full_name': 'Ahmad Fuad, S.Pd.'
        },
        {
            'username':'ismail',
            'password':'password123',
            'division':'SMK',
            'gender': GenderType.MALE,
            'full_name':'Ismail, S.T.'
        },
        {
            'username':'pamelri',
            'password':'password123',
            'division':'SMP',
            'gender': GenderType.MALE,
            'full_name':'Pamel Riyadi, S.Pd.'
        }
        
    ]

    for user_data in sample_users:
        if User.query.filter_by(username=user_data['username']).first() is None:
            user = User(
                username=user_data['username'],
                division=user_data['division'],
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
