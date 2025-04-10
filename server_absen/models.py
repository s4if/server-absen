from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from enum import Enum as PyEnum
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

db = SQLAlchemy()

class LocationMixin:
    # Increased precision for PostgreSQL
    latitude = db.Column(db.Numeric(precision=10, scale=8), nullable=False)
    longitude = db.Column(db.Numeric(precision=12, scale=9), nullable=False)
    
    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90', name='check_latitude'),
        CheckConstraint('longitude BETWEEN -180 AND 180', name='check_longitude'),
    )

class TimestampMixin:
    # Using PostgreSQL's TIMESTAMP WITH TIME ZONE
    created_at = db.Column(db.DateTime(timezone=True), 
                          default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(pytz.timezone('Asia/Jakarta')),
        onupdate=lambda: datetime.now(pytz.timezone('Asia/Jakarta'))
    )

class SoftDeleteMixin:
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    def soft_delete(self):
        self.deleted_at = datetime.now(pytz.timezone('Asia/Jakarta'))

class PasswordMixin:
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

class User(TimestampMixin, SoftDeleteMixin, PasswordMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    division = db.Column(db.String(80), nullable=False, index=True)
    full_name = db.Column(db.String(120))
    gender = db.Column(db.Enum(GenderType, name='gender_type'), nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    
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

class Attendance(TimestampMixin, db.Model):
    __tablename__ = 'attendances'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'attendance_date', name='uq_user_date'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime(timezone=True), nullable=False)
    check_in_location_id = db.Column(db.Integer, db.ForeignKey('attendance_locations.id'), nullable=False)
    check_out = db.Column(db.DateTime(timezone=True), nullable=True)
    check_out_location_id = db.Column(db.Integer, db.ForeignKey('attendance_locations.id'), nullable=True)

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
    attendance_time = db.Column(db.DateTime(timezone=True), nullable=False)
    agenda_name = db.Column(db.String(120), nullable=False)
    location_name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=True)

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
    frequency = db.Column(db.Integer, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    for_division = db.Column(db.String(20), nullable=True)

    participants = db.relationship('User', secondary='agenda_participants', backref=db.backref('agendas', lazy='select'))

    def __repr__(self):
        return f'<Agenda {self.name} {self.start_time}>'
    
class AgendaParticipant(db.Model):
    __tablename__ = 'agenda_participants'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    agenda_id = db.Column(db.Integer, db.ForeignKey('agendas.id'), primary_key=True)

# Indexes
db.Index('idx_attendance_user_date', 'user_id', 'attendance_date')
db.Index('idx_agenda_start_end', 'start_date', 'end_date')