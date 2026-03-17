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
        
        # --- Automated Migration Logic (Research Data Consistency) ---
        from sqlalchemy import text
        
        def safe_add_column(table, col_name, col_def):
            try:
                conn = db.engine.connect()
                # Check if column exists
                if db.engine.name == 'sqlite':
                    res = conn.execute(text(f"PRAGMA table_info({table})"))
                    cols = [r[1] for r in res]
                else: # Postgres
                    res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"))
                    cols = [r[0] for r in res]
                
                if col_name not in cols:
                    print(f"      + Migrating: Adding {table}.{col_name}...")
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"      ! Error migrating {table}.{col_name}: {e}")

        # Ensure NEW columns exist (if DB was created earlier)
        safe_add_column("dynamic_session", "mode", "VARCHAR(20) DEFAULT 'static'")
        safe_add_column("dynamic_session", "exp_earned", "INTEGER DEFAULT 0")
        safe_add_column("dynamic_session", "level_before", "INTEGER DEFAULT 1")
        safe_add_column("dynamic_session", "level_after", "INTEGER DEFAULT 1")
        safe_add_column("dynamic_session", "level_ups_occurred", "INTEGER DEFAULT 0")
        safe_add_column("sign_attempt", "exp_earned", "INTEGER DEFAULT 0")

        # --- Data Cleanup Logic ---
        try:
            # 1. Update course='static' to 'alphabets' (consistency with stats)
            db.session.execute(text("UPDATE dynamic_session SET course='alphabets' WHERE course='static'"))
            db.session.execute(text("UPDATE sign_attempt SET course='alphabets' WHERE course='static'"))
            
            # 2. Update course='alphabets_ai' to 'alphabets'
            db.session.execute(text("UPDATE dynamic_session SET course='alphabets', mode='ai' WHERE course='alphabets_ai'"))
            db.session.execute(text("UPDATE sign_attempt SET course='alphabets' WHERE course='alphabets_ai'"))
            
            # 3. Tag existing 'alphabets' sessions with mode='dynamic' if mode is missing/default
            db.session.execute(text("UPDATE dynamic_session SET mode='dynamic' WHERE course='alphabets' AND (mode IS NULL OR mode='static' OR mode='')"))
            
            db.session.commit()
            print('      + Research data labels standardized.')
        except Exception as e:
            print(f"      ! Error during data cleanup: {e}")

        print('Database tables and schema migrations verified/created.')


    # --- Automated Seeding ---
    try:
        from .gamification import seed_achievements
        from .models import User, UserProgress
        
        with app.app_context():
            # 1. Seed Achievements (Idempotent)
            seed_achievements()
            
            # 2. Initialize UserProgress for existing users (Idempotent)
            users = User.query.all()
            created_count = 0
            for user in users:
                exists = UserProgress.query.filter_by(user_id=user.id).first()
                if not exists:
                    prog = UserProgress(user_id=user.id)
                    db.session.add(prog)
                    created_count += 1
            
            if created_count > 0:
                db.session.commit()
                print(f"      + Initialized UserProgress for {created_count} users")
                
    except Exception as e:
        print(f"      ! Error during automated seeding: {e}")

