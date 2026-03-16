from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
import os

db = SQLAlchemy()
DB_NAME = "instance/database.db"


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sad2wqyt3'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(DB_NAME)}'
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
    db_dir = os.path.dirname(os.path.abspath(DB_NAME))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    if not os.path.exists(os.path.abspath(DB_NAME)):
        with app.app_context():
            db.create_all()
            print('Database created!')
