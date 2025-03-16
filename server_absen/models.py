from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from enum import Enum as PyEnum  # Import Python's Enum
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

# Note: Timezone is hardcoded to Asia/Jakarta

db = SQLAlchemy()

class LocationMixin:
    latitude = db.Column(db.Numeric(precision=9, scale=6), nullable=False)
    longitude = db.Column(db.Numeric(precision=9, scale=6), nullable=False)
    
    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90', name='check_latitude'),
        CheckConstraint('longitude BETWEEN -180 AND 180', name='check_longitude'),
    )

class TimestampMixin:
    # Use timezone-aware Asia/Jakarta timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )

class SoftDeleteMixin:
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)  # Soft delete timestamp

    def soft_delete(self):
        self.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))

class PasswordMixin:
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
# Enums
# Use native ENUM for PostgreSQL and CHECK constraints for SQLite
class GenderType(PyEnum):
    MALE = "L"
    FEMALE = "P"

class AttendanceStatusType(PyEnum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"

class Admin(TimestampMixin, PasswordMixin, db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120))

    def __repr__(self):
        return f'<Admin {self.username}>'


class User(TimestampMixin, SoftDeleteMixin, PasswordMixin, db.Model): # untuk guru pakai ini
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    division = db.Column(db.String(80), nullable=False, index=True)
    full_name = db.Column(db.String(120))
    gender = db.Column(db.Enum(GenderType, name='gender_type'), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    attendances = db.relationship('Attendance', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class AttendanceLocation(TimestampMixin, SoftDeleteMixin, LocationMixin, db.Model):
    __tablename__ = 'attendance_locations'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    short_name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<AttendanceLocation {self.name}>'

# absensi kerja harian
class Attendance(TimestampMixin, db.Model):
    __tablename__ = 'attendances'

    # Add a unique constraint for (user_id, attendance_date)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'attendance_date', name='uq_user_date'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_in_location_id = db.Column(db.Integer, db.ForeignKey('attendance_locations.id'), nullable=False)
    check_out = db.Column(db.DateTime, nullable=True)
    check_out_location_id = db.Column(db.Integer, db.ForeignKey('attendance_locations.id'), nullable=True)

    # relationship
    check_in_location = db.relationship('AttendanceLocation', foreign_keys=[check_in_location_id])
    check_out_location = db.relationship('AttendanceLocation', foreign_keys=[check_out_location_id])

    status = db.Column(db.Enum(AttendanceStatusType, name='attendance_status'), default=AttendanceStatusType.PRESENT)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Attendance {self.user_id} {self.check_in.date()}>'

class SelfReportedAttendance(TimestampMixin, LocationMixin, db.Model):
    __tablename__ = 'self_reported_attendances'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_time = db.Column(db.DateTime, nullable=False)
    agenda_name = db.Column(db.String(120), nullable=False)
    location_name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=True)  # dari google api? client/server? add to TODO
    # location already on LocationMixin

    def __repr__(self):
        return f'<SelfReportedAttendance {self.user_id} {self.attendance_time}>'
    
class Agenda(TimestampMixin, SoftDeleteMixin, LocationMixin, db.Model):
    __tablename__ = 'agendas'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    type = db.Column(db.Enum('routine', 'flexible-routine', 'oneoff', name='agenda_type'), nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)

    # frequency (in days) for routine and flexible-routine
    frequency = db.Column(db.Integer, nullable=True)

    # for routine and oneoff (in oneoff end_date and frequency is null)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # if participant is null, the agenda apply to all users unless division is not null
    participants = db.relationship('User', secondary='agenda_participants', backref=db.backref('agendas', lazy='select'))
    # select participant by division, I don't know if it is needed, but nice to have. Support multi division using ,
    for_division = db.Column(db.String(20), nullable=True)

    def __repr__(self):
        return f'<Agenda {self.name} {self.start_time}>'
    
class AgendaParticipant(db.Model):
    __tablename__ = 'agenda_participants'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    agenda_id = db.Column(db.Integer, db.ForeignKey('agendas.id'), primary_key=True)

# indexes
db.Index('idx_attendance_user_date', 'user_id', 'attendance_date')
db.Index('idx_agenda_start_end', 'start_date', 'end_date')