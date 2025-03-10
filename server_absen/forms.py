from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, PasswordField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=25)])
    submit = SubmitField('Login')

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    full_name = StringField('Nama Lengkap', validators=[DataRequired(), Length(min=3, max=60)])
    division = SelectField('Unit', choices=[('SMA', 'SMA'), ('SMK', 'SMK'), ('SMP', 'SMP'), ('Non-Pengajar', 'Non-Pengajar')], validators=[DataRequired()])
    gender = SelectField('Jenis Kelamin', choices=[('L', 'Laki-laki'), ('P', 'Perempuan')], validators=[DataRequired()])
    submit = SubmitField('Simpan')

class AddUserForm(EditUserForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=25)])

class AttendanceLocationForm(FlaskForm):
    name = StringField('Nama Lokasi', validators=[DataRequired(), Length(max=120)])
    short_name = StringField('Kode Lokasi', validators=[DataRequired(), Length(max=20)])
    description = StringField('Deskripsi', validators=[Length(max=200)])
    latitude = FloatField('Latitude', validators=[DataRequired(), NumberRange(min=-90, max=90)])
    longitude = FloatField('Longitude', validators=[DataRequired(), NumberRange(min=-180, max=180)])
    submit = SubmitField('Save')