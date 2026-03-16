import os


class Config:
    """Base configuration loaded from environment variables."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-key-change-in-production')

    # Database
    # Railway provides DATABASE_URL with "postgres://" prefix; SQLAlchemy needs "postgresql://"
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url or f"sqlite:///{os.path.abspath('instance/database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Debug mode — disabled in production by default
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
