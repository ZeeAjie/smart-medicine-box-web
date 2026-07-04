import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, render_template, redirect, url_for, flash, session, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from forms import RegisterForm, LoginForm, TagRegistrationForm, ScheduleForm
from flask_bootstrap import Bootstrap5

app= Flask(__name__)
app.config['SECRET_KEY'] = '@smart22medicine44box88#'
bootstrap=Bootstrap5(app)

login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view="login"

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

class Base(DeclarativeBase):
    pass

#  sqlite:///medbox.db

app.config ['SQLALCHEMY_DATABASE_URI']= os.environ.get("DATABASE_URL")

#app.config ['SQLALCHEMY_DATABASE_URI']='postgresql+psycopg2://postgres.uspnsztvcuooxlzqfyro:FYPsmartmedbox#1@aws-0-eu-central-1.pooler.supabase.com:5432/postgres'

app.config['PERMANENT_SESSION_LIFETIME']=timedelta(minutes=10)

db=SQLAlchemy(model_class=Base)
db.init_app(app)

class User(UserMixin, db.Model):
    __tablename__="users"
    id:Mapped[int]=mapped_column(Integer, primary_key=True)
    email:Mapped[str]=mapped_column(String(250), unique=True, nullable=False)
    password:Mapped[str]=mapped_column(String(250), nullable=False)
    role:Mapped[str]=mapped_column(String(250), nullable=False)
    backup_pin:Mapped[str]=mapped_column(String(100), nullable=False)

class RFIDTag(db.Model):
    __tablename__="rfid_tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid:Mapped[str]=mapped_column(String(250), unique=True, nullable=False)
    name:Mapped[str]=mapped_column(String(250), nullable=False)
    is_master:Mapped[bool]=mapped_column(Boolean, nullable=True)
    user_id: Mapped[int]=mapped_column(Integer, ForeignKey('users.id'),nullable=False)
    schedules= relationship("Schedule", back_populates="assigned_tag")

class Schedule(db.Model):
    __tablename__="schedules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    compartment_no: Mapped[int]= mapped_column(Integer, nullable=False)
    label:Mapped[str]= mapped_column(String(250), nullable=False)
    description:Mapped[str]=mapped_column(String, nullable=True)
    schedule_time:Mapped[str]=mapped_column(String(250), nullable=False)
    rfid_tag_id:Mapped[int]=mapped_column(Integer, ForeignKey("rfid_tags.id"))
    assigned_tag= relationship("RFIDTag", back_populates="schedules")

class Accesslog(db.Model):
    __tablename__="access_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp:Mapped[datetime]=mapped_column(default=lambda: datetime.now(ZoneInfo("Africa/Lagos")), nullable=False)
    compartment_no:Mapped[int]=mapped_column(Integer, nullable=True)
    event_type: Mapped[str]=mapped_column(String(250), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def home():
    recent_logs=db.session.execute(db.select(Accesslog).order_by(Accesslog.timestamp.desc()).limit(5)).scalars().all()
    missed_dosage=db.session.execute(db.select(Accesslog).where(Accesslog.event_type=="Missed Dosage")).scalars().all()
    missed_dosage_today=False
    for log in missed_dosage:
        if log.timestamp.date()==datetime.now(ZoneInfo("Africa/Lagos")).date():
            missed_dosage_today=True
    return render_template("index.html", logs=recent_logs, missed_dosage=missed_dosage_today)

@app.route('/create', methods=["POST", "GET"])
def create():
    form=RegisterForm()
    if form.validate_on_submit():
        email=form.email.data
        password= generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        role= form.role.data
        backup_pin = form.backup_pin.data
        user=db.session.execute(db.select(User). where(User.email==email)).scalar()

        if user:
            flash ("Already registered")
            return redirect (url_for("login"))
        new_user= User(email=email,
                       password=password,
                       role=role,
                       backup_pin=backup_pin)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("create.html", form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        email=form.email.data
        password=form.password.data
        user=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if not user:
            flash("Invalid email. Try again.")
            return redirect(url_for("login"))
        elif not check_password_hash(user.password, password):
            flash("Incorrect password. Try again.")
            return redirect(url_for("login"))
        else:
            login_user(user)
            session.permanent= True
            return redirect(url_for("home"))
    return render_template("logging.html", form=form)

@app.route('/tag_register',  methods=["GET", "POST"])
@login_required
def tag_register():
    form=TagRegistrationForm()
    if form.validate_on_submit():
        uid=form.uid.data
        name=form.name.data
        is_master=form.is_master_key.data
        tag_uid=db.session.execute(db.select(RFIDTag).where(RFIDTag.uid==uid)).scalar()
        if tag_uid:
            flash("Already registered.")
            return redirect(url_for("tag_register"))
        new_tag= RFIDTag(uid=uid,
                         name=name,
                         is_master=is_master,
                         user_id=current_user.id)
        db.session.add(new_tag)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("tag_register.html", form=form)

@app.route('/set_schedule',  methods=["GET", "POST"])
@login_required
def set_schedule():
    form=ScheduleForm()
    all_tags=db.session.execute(db.select(RFIDTag)).scalars().all()
    form.assigned_tag.choices=[(tag.id, tag.name) for tag in all_tags]
    if form.validate_on_submit():
        compartment_no=form.compartment_no.data
        dosage_label=form.dosage_label.data
        description=form.description.data
        schedule_time=str(form.schedule_time.data)
        assigned_tag=form.assigned_tag.data
        old_schedule=db.session.execute(db.select(Schedule).where(Schedule.compartment_no==compartment_no)).scalar()
        if old_schedule:
            db.session.delete(old_schedule)
        new_schedule=Schedule(compartment_no=compartment_no,
                              label=dosage_label,
                              description=description,
                              schedule_time=schedule_time,
                              rfid_tag_id=assigned_tag)
        db.session.add(new_schedule)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("set_schedule.html", form=form)

@app.route('/logs')
@login_required
def logs():
    all_logs=db.session.execute(db.select(Accesslog).order_by(Accesslog.id.desc())).scalars().all()
    return render_template("logs.html", all_logs=all_logs)


@app.route('/view_schedule/<int:number>', methods=["GET", "POST"])
@login_required
def view_schedule(number):
    schedules=db.session.execute(db.select(Schedule).where(Schedule.compartment_no==number)).scalar()
    return render_template("view_schedule.html", number=number, schedule=schedules)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

#todo: update this route for offline syncing
@app.route('/api/log', methods=["POST"])
def log_event():
    data=request.get_json()
    compartment= data.get('compartment_no')
    event = data.get('event_type')
    new_log= Accesslog(compartment_no=compartment,
                       event_type=event)
    db.session.add(new_log)
    db.session.commit()

    return jsonify({"status":"success", "message": "Log securely saved to database."})

@app.route('/api/schedule', methods=["GET"])
def schedule():
    schedules=db.session.execute(db.select(Schedule)).scalars().all()
    all_tag = db.session.execute(db.select(RFIDTag)).scalars().all()
    admin = db.session.execute(db.select(User).where(User.role=="Admin")).scalar()
    schedule_list=[]
    for data in schedules:
        schedule_dict={
            "id":data.id,
            "compartment_no":data.compartment_no,
            "label": data.label,
            "schedule_time":data.schedule_time
        }
        schedule_list.append(schedule_dict)

    return jsonify({
        "global_pin":admin.backup_pin if admin else None,
        "valid_tags":[t.uid for t in all_tag],
        "schedules":schedule_list}
    )

@app.route('/api/verify', methods=["POST"])
def verify():
    data=request.get_json()
    scanned_uid= data.get('rfid_tag_id')
    entered_pin= data.get('users')
    tag=db.session.execute(db.select(RFIDTag).where(RFIDTag.uid==scanned_uid)).scalar()
    pin = db.session.execute(db.select(User).where(User.backup_pin == entered_pin)).scalar()
    if tag and pin:
        return jsonify({"status": "authorized",
                        "message": "Access Granted"})
    else:
        return jsonify({"status": "unauthorized",
                        "message": "Access Denied"})


if __name__=="__main__":
    app.run(host="0.0.0.0", debug=True)