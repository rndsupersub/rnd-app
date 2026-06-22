from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'viewer')
            
            if User.query.filter_by(username=username).first():
                flash('Username sudah terdaftar!', 'danger')
                return render_template('register.html')
            if User.query.filter_by(email=email).first():
                flash('Email sudah terdaftar!', 'danger')
                return render_template('register.html')
            
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            print(f"ERROR REGISTER: {e}")
            flash(f'Terjadi kesalahan: {e}', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash(f'Selamat datang, {user.username}!', 'success')
                return redirect(url_for('routes.dashboard'))
            else:
                flash('Username atau password salah!', 'danger')
        except Exception as e:
            print(f"ERROR LOGIN: {e}")
            flash(f'Terjadi kesalahan: {e}', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))