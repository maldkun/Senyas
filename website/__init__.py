from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
DB_NAME = "instance/database.db"


def create_app():
    app = Flask(__name__)

    # Load configuration from environment variables (via config.py)
    from config import Config
    app.config.from_object(Config)

    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .views_ai import views_ai
    app.register_blueprint(views_ai, url_prefix='/')

    from .models import User, Feedback, DynamicSession, SignAttempt, UserSignStats
    from .models import UserProgress, Achievement, UserAchievement, EXPTransaction

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.landingpage'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        try:
            return User.query.get(int(id))
        except Exception as e:
            print(f"Error loading user {id}: {e}")
            return None

    return app


def create_database(app):
    """Create database tables if they don't already exist.
    Works for both SQLite (local dev) and PostgreSQL (production).
    """
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

    # For SQLite only: ensure the instance/ directory exists
    if db_uri.startswith('sqlite'):
        db_dir = os.path.dirname(os.path.abspath(DB_NAME))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    # Always create tables (safe – only creates missing tables, never drops existing ones)
    with app.app_context():
        db.create_all()
        print('Database tables verified/created.')

