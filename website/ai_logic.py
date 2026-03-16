import math
import json
from datetime import datetime
from .models import db, User, UserSignStats, DynamicSession, SignAttempt
from sqlalchemy.sql import func

class AIDifficultyEngine:
    
    @staticmethod
    def check_unlock_status(user_id):
        """
        Check if AI mode is unlocked for the user.
        Requirements:
        - 4+ Dynamic Sessions
        - 50+ Total Attempts
        - 20+ Unique Signs Practiced
        """
        # Get dynamic sessions count
        total_sessions = DynamicSession.query.filter_by(
            user_id=user_id
        ).filter(DynamicSession.completed_at.isnot(None)).count()
        
        # Get total attempts
        total_attempts = SignAttempt.query.filter_by(user_id=user_id).count()
        
        # Get unique signs
        unique_signs = UserSignStats.query.filter_by(
            user_id=user_id,
            course='alphabets'  # AI mode currently focuses on alphabets
        ).count()
        
        # Requirements
        req_sessions = 4
        req_attempts = 50
        req_unique = 20
        
        is_unlocked = (
            total_sessions >= req_sessions and
            total_attempts >= req_attempts and
            unique_signs >= req_unique
        )
        
        return {
            'is_unlocked': is_unlocked,
            'progress': {
                'sessions': {'current': total_sessions, 'required': req_sessions},
                'attempts': {'current': total_attempts, 'required': req_attempts},
                'unique_signs': {'current': unique_signs, 'required': req_unique}
            }
        }

    @staticmethod
    def get_user_stats(user_id):
        """Get all sign stats for the user"""
        return UserSignStats.query.filter_by(
            user_id=user_id, 
            course='alphabets'
        ).all()

    @staticmethod
    def calculate_sign_metrics(stats):
        """
        Calculate AI metrics for a single sign stat entry.
        Returns dict with: predicted_success, weakness_score, study_time, threshold, difficulty_label
        """
        if not stats:
            # Cold start / No data
            return {
                'predicted_success': 0.3,
                'weakness_score': 0.7,
                'study_time': 8.0,
                'threshold': 60,
                'difficulty_label': 'Challenging',
                'difficulty_color': 'red'
            }

        # Step 1: Extract Metrics
        total = stats.total_attempts
        if total == 0:
            return AIDifficultyEngine.calculate_sign_metrics(None)
            
        accuracy_rate = stats.correct_count / total
        confidence_score = (stats.avg_confidence or 0) / 100.0
        
        # Parsing last_5_attempts
        try:
            last_5 = json.loads(stats.last_5_attempts) if stats.last_5_attempts else []
        except:
            last_5 = []
            
        if not last_5:
            consistency_score = 0.5 # Neutral if no recent history
        else:
            consistency_score = sum(1 for x in last_5 if x) / len(last_5)

        # Days since last practice
        if stats.last_practiced_at:
            # properly handle timezone aware datetimes if needed, assuming generic check here
            # using diff in days
            delta = datetime.now() - stats.last_practiced_at.replace(tzinfo=None) # simplistic
            days_since = delta.days
        else:
            days_since = 0

        # Step 2: Recency Factor
        recency_factor = math.exp(-0.3 * days_since)

        # Step 3: Predicted Success
        predicted_success = (
            (0.4 * accuracy_rate) +
            (0.3 * confidence_score) +
            (0.2 * consistency_score) +
            (0.1 * recency_factor)
        )
        predicted_success = max(0, min(1, predicted_success))

        # Step 4: Weakness Score
        weakness_score = 1.0 - predicted_success
        
        # Step 5: Spaced Repetition Boost
        if days_since > 5 and predicted_success < 0.7:
            weakness_score += 0.1

        # PER-SIGN STUDY TIME
        study_time = 3 + (weakness_score * 7)
        study_time = max(3, min(10, study_time))

        # PER-SIGN VALIDATION THRESHOLD
        threshold = 60 + (predicted_success * 25)
        threshold = max(60, min(85, threshold))

        # DIFFICULTY LABEL
        if predicted_success > 0.75:
            label = "Easy"
            color = "green"
        elif predicted_success >= 0.5:
            label = "Moderate"
            color = "yellow"
        else:
            label = "Challenging"
            color = "red"

        return {
            'predicted_success': predicted_success,
            'weakness_score': weakness_score,
            'study_time': round(study_time, 1),
            'threshold': round(threshold, 0),
            'difficulty_label': label,
            'difficulty_color': color
        }

    @staticmethod
    def generate_session_plan(user_id):
        """
        Generate a 15-sign personalized session plan.
        """
        # Get all existing stats
        stats_list = AIDifficultyEngine.get_user_stats(user_id)
        stats_map = {s.sign_id: s for s in stats_list}
        
        all_signs = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        
        scored_signs = []
        
        for sign in all_signs:
            stats = stats_map.get(sign)
            metrics = AIDifficultyEngine.calculate_sign_metrics(stats)
            scored_signs.append({
                'sign': sign,
                'metrics': metrics
            })
            
        # Sort by weakness (descending)
        scored_signs.sort(key=lambda x: x['metrics']['weakness_score'], reverse=True)
        
        # Tiering Selection
        # Weak Tier: Top 8
        weak_tier = scored_signs[:8]
        # Moderate Tier: Next 4
        moderate_tier = scored_signs[8:12]
        # Strong Tier: Next 3
        strong_tier = scored_signs[12:15]
        
        # If we don't have enough signs (e.g. somehow < 15 total), just take what we have
        # But here we have 26 alphabets always.

        # Override difficulty_label to match selection tier (for consistent reporting)
        for item in weak_tier:
            item['metrics']['difficulty_label'] = 'Challenging'
        for item in moderate_tier:
            item['metrics']['difficulty_label'] = 'Moderate'
        for item in strong_tier:
            item['metrics']['difficulty_label'] = 'Easy'
        
        # Combine WITHOUT final shuffle - this preserves tier distribution!
        # WEAKEST FIRST (Strict Order)
        selection = weak_tier + moderate_tier + strong_tier
        
        return selection

    @staticmethod
    def update_stats_after_attempt(user_id, sign_id, is_correct, confidence):
        """
        Update UserSignStats after a single attempt
        """
        stats = UserSignStats.query.filter_by(
            user_id=user_id,
            sign_id=sign_id,
            course='alphabets'
        ).first()
        
        if not stats:
            stats = UserSignStats(
                user_id=user_id,
                sign_id=sign_id,
                course='alphabets',
                total_attempts=0,
                correct_count=0,
                avg_confidence=0.0,
                last_5_attempts="[]"
            )
            db.session.add(stats)
        
        # Update basics
        stats.total_attempts += 1
        if is_correct:
            stats.correct_count += 1
            
        # Update rolling average confidence
        # Average = ((OldAvg * (Total-1)) + NewConf) / Total
        current_avg = stats.avg_confidence or 0.0
        new_avg = ((current_avg * (stats.total_attempts - 1)) + confidence) / stats.total_attempts
        stats.avg_confidence = new_avg
        
        # Update last_5_attempts
        try:
            last_5 = json.loads(stats.last_5_attempts)
        except:
            last_5 = []
            
        last_5.append(is_correct)
        if len(last_5) > 5:
            last_5.pop(0)
            
        stats.last_5_attempts = json.dumps(last_5)
        stats.last_practiced_at = func.now()
        
        db.session.commit()
