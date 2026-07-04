from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, SelectField, TimeField
from wtforms.validators import DataRequired, Email, Optional, EqualTo, Length


class RegisterForm(FlaskForm):
    email= StringField("Email", validators=[DataRequired()])
    password= PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(),
                                                             EqualTo('password', message='Passwords must match')])
    role=SelectField("Role", validators=[DataRequired()],
                     choices=[('Caregiver', 'Primary Caregiver'), ('Doctor', 'Doctor'), ('Admin', 'System Admin')])
    backup_pin=StringField("Backup PIN(4 digits)", validators=[DataRequired(), Length(min=4, max=4, message="PIN must be exactly 4 digits")])
    submit= SubmitField("Register")

class LoginForm(FlaskForm):
    email= StringField("Email", validators=[DataRequired()])
    password= PasswordField("Password", validators=[DataRequired()])
    submit= SubmitField("Log In")

class TagRegistrationForm(FlaskForm):
    uid= StringField("UID", validators=[DataRequired()])
    name= StringField("Owner name", validators=[DataRequired()])
    is_master_key= BooleanField ("Master Key Status")
    submit = SubmitField("Register Tag")

class ScheduleForm(FlaskForm):
    compartment_no= SelectField("Compartment Number", validators=[DataRequired()],
                                choices=[(1, "Compartment 1"), (2, "Compartment 2"), (3, "Compartment 3")], coerce=int)
    dosage_label= StringField("Dosage Label", validators=[DataRequired()])
    description= StringField("Description", validators=[Optional()])
    schedule_time= TimeField ("Schedule Time", validators=[DataRequired()])
    assigned_tag= SelectField("Assigned Tag", validators=[DataRequired()], choices=[])
    submit = SubmitField("Set Schedule")
