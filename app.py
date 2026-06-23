from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

# ==================== INISIALISASI APLIKASI ====================
app = Flask(__name__)

# Konfigurasi Keamanan
app.config['SECRET_KEY'] = 'Fathan12345*****'

# Konfigurasi Database (Menggunakan nama file baru untuk memastikan struktur bersih)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/rnd_app_fix.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==================== INISIALISASI EXTENSION ====================
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Silakan login terlebih dahulu."
csrf = CSRFProtect(app)

# ==================== LOAD USER ====================
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== IMPORT ROUTES ====================
from auth import auth_bp
from routes import routes_bp

app.register_blueprint(auth_bp)
app.register_blueprint(routes_bp)

# ==================== BUAT TABEL DATABASE ====================
with app.app_context():
    db.create_all()
    print("✅ Database tables created!")

# ==================== MENJALANKAN APLIKASI ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# ==================== UNTUK VERCEL ====================
app = app