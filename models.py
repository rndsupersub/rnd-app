from app import db
from flask_login import UserMixin
from datetime import datetime

# ==================== TABEL USER ====================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='viewer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relasi
    projects = db.relationship('Project', backref='user', lazy=True)
    swots = db.relationship('SWOT', backref='user', lazy=True)
    pestles = db.relationship('PESTLE', backref='user', lazy=True)
    bmcs = db.relationship('BMC', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

# ==================== TABEL PROYEK ====================
class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_type = db.Column(db.String(50), default='Main')
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='On Track')
    google_drive_link = db.Column(db.String(500), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Project {self.name}>'

# ==================== TABEL SWOT ====================
class SWOT(db.Model):
    __tablename__ = 'swot'
    id = db.Column(db.Integer, primary_key=True)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    opportunities = db.Column(db.Text)
    threats = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)  # ← NULLABLE

    project = db.relationship('Project', backref='swots')

    def __repr__(self):
        return f'<SWOT for user {self.user_id}>'

# ==================== TABEL PESTLE ====================
class PESTLE(db.Model):
    __tablename__ = 'pestle'
    id = db.Column(db.Integer, primary_key=True)
    political = db.Column(db.Text)
    economic = db.Column(db.Text)
    social = db.Column(db.Text)
    technological = db.Column(db.Text)
    legal = db.Column(db.Text)
    environmental = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)  # ← NULLABLE

    project = db.relationship('Project', backref='pestles')

    def __repr__(self):
        return f'<PESTLE for user {self.user_id}>'

# ==================== TABEL BMC ====================
class BMC(db.Model):
    __tablename__ = 'bmc'
    id = db.Column(db.Integer, primary_key=True)
    key_partners = db.Column(db.Text)
    key_activities = db.Column(db.Text)
    key_resources = db.Column(db.Text)
    value_proposition = db.Column(db.Text)
    customer_relationships = db.Column(db.Text)
    channels = db.Column(db.Text)
    customer_segments = db.Column(db.Text)
    cost_structure = db.Column(db.Text)
    revenue_streams = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)  # ← NULLABLE

    project = db.relationship('Project', backref='bmcs')

    def __repr__(self):
        return f'<BMC for user {self.user_id}>'