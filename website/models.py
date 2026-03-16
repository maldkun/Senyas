from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='feedback_list')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    fsl_progress = db.Column(db.Integer, default=0)  # Number of parts completed (0-5)
    
    # Dynamic Difficulty unlock status
    dynamic_alphabets_unlocked = db.Column(db.Boolean, default=False)
    dynamic_words_unlocked = db.Column(db.Boolean, default=False)
    dynamic_phrases_unlocked = db.Column(db.Boolean, default=False)
    
    feedbacks = db.relationship('Feedback')


class DynamicSession(db.Model):
    """Tracks each Dynamic practice session"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course = db.Column(db.String(50))  # 'alphabets', 'words', 'phrases'
    mode = db.Column(db.String(20), default='static')  # 'static', 'dynamic', 'ai'
    started_at = db.Column(db.DateTime(timezone=True), default=func.now())
    completed_at = db.Column(db.DateTime(timezone=True))
    total_signs = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
    final_study_time = db.Column(db.Integer)  # seconds
    final_threshold = db.Column(db.Integer)  # percentage
    # Gamification columns
    exp_earned = db.Column(db.Integer, default=0)
    level_before = db.Column(db.Integer, default=1)
    level_after = db.Column(db.Integer, default=1)
    level_ups_occurred = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref='dynamic_sessions')


class SignAttempt(db.Model):
    """Records individual sign attempts within sessions"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('dynamic_session.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sign_id = db.Column(db.String(50))  # 'A', 'B', 'HELLO', etc.
    course = db.Column(db.String(50))
    was_correct = db.Column(db.Boolean)
    ai_detected_sign = db.Column(db.String(50))
    ai_confidence = db.Column(db.Float)
    validation_threshold = db.Column(db.Integer)
    study_time_used = db.Column(db.Integer)
    
    # Detailed Context
    study_time_limit = db.Column(db.Float)  # The limit given for this attempt (e.g. 5.0)
    current_threshold = db.Column(db.Integer)  # The confidence threshold at this time (e.g. 70)
    
    # Batch tracking
    batch_index = db.Column(db.Integer)
    batch_size = db.Column(db.Integer)
    study_order_index = db.Column(db.Integer)
    performance_order_index = db.Column(db.Integer)
    
    # Gamification
    exp_earned = db.Column(db.Integer, default=0)
    
    attempted_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    session = db.relationship('DynamicSession', backref='attempts')
    user = db.relationship('User', backref='sign_attempts')


class UserSignStats(db.Model):
    """Aggregated performance statistics per sign"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sign_id = db.Column(db.String(50))
    course = db.Column(db.String(50))
    total_attempts = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    last_practiced_at = db.Column(db.DateTime(timezone=True))
    
    # AI Mode Specific Stats
    avg_confidence = db.Column(db.Float, default=0.0)
    last_5_attempts = db.Column(db.String(100), default="[]")  # JSON List of booleans e.g. "[true, false, true]"
    
    user = db.relationship('User', backref='sign_stats')
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'sign_id', 'course', name='_user_sign_course_uc'),)


# ============================================================================
# Gamification Models
# ============================================================================

class UserProgress(db.Model):
    """Tracks overall EXP, level, streaks, and counters per user"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    total_exp = db.Column(db.Integer, default=0)
    current_level = db.Column(db.Integer, default=1)
    current_streak_days = db.Column(db.Integer, default=0)
    longest_streak_days = db.Column(db.Integer, default=0)
    last_practice_date = db.Column(db.Date, nullable=True)
    total_sessions_completed = db.Column(db.Integer, default=0)
    total_signs_attempted = db.Column(db.Integer, default=0)
    total_signs_correct = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    user = db.relationship('User', backref='progress')


class Achievement(db.Model):
    """Master list of all available achievements"""
    id = db.Column(db.Integer, primary_key=True)
    achievement_key = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'performance','engagement','streak','mode','hidden'
    badge_icon = db.Column(db.String(20))  # emoji
    exp_reward = db.Column(db.Integer, default=0)
    is_hidden = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())


class UserAchievement(db.Model):
    """Tracks which achievements each user has unlocked"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime(timezone=True), default=func.now())
    is_showcased = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='user_achievements')
    achievement = db.relationship('Achievement', backref='user_achievements')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='_user_achievement_uc'),)


class EXPTransaction(db.Model):
    """Detailed audit log of all EXP earned"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('dynamic_session.id'), nullable=True)
    sign_attempt_id = db.Column(db.Integer, db.ForeignKey('sign_attempt.id'), nullable=True)
    exp_amount = db.Column(db.Integer, nullable=False)
    exp_source = db.Column(db.String(100))  # e.g. 'sign_correct', 'batch_complete'
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    user = db.relationship('User', backref='exp_transactions')
