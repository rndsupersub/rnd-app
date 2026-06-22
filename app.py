from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# ==================== INISIALISASI APLIKASI ====================
app = Flask(__name__)

# Konfigurasi keamanan (kunci rahasia - SUDAH DIGANTI!)
app.config['SECRET_KEY'] = 'Fathan12345*****'

# Konfigurasi database (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==================== INISIALISASI EXTENSION ====================
db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Halaman yang akan diarahkan jika user belum login
login_manager.login_view = 'login'
login_manager.login_message = "Login heula atuh bray."

# Untuk keamanan formulir (CSRF Protection)
csrf = CSRFProtect(app)

# ==================== LOAD USER ====================
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== IMPORT ROUTES ====================
from auth import auth_bp
from routes import routes_bp

# Register blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(routes_bp)

# ==================== MENJALANKAN APLIKASI ====================
if __name__ == '__main__':
    # Buat database jika belum ada
    with app.app_context():
        db.create_all()
        print("Database berhasil dibuat!")
    
    # Jalankan server
    app.run(debug=True, host='0.0.0.0', port=5000)
    # ==================== UNTUK VERCEL ====================
app = app