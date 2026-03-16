from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .models import db, User, UserSignStats, DynamicSession, SignAttempt
from .ai_logic import AIDifficultyEngine
from . import gamification as gami
from datetime import datetime

views_ai = Blueprint('views_ai', __name__)


@views_ai.route('/courseai')
@login_required
def courseai():
    """
    Render the AI-Driven Difficulty Mode page.
    """
    return render_template('courseai.html')


@views_ai.route('/api/ai/unlock_status', methods=['GET'])
@login_required
def get_unlock_status():
    """
    Check if the user has unlocked AI mode.
    """
    status = AIDifficultyEngine.check_unlock_status(current_user.id)
    return jsonify(status)


@views_ai.route('/api/ai/session_count', methods=['GET'])
@login_required
def get_session_count():
    """
    Get the count of completed AI sessions for the current user.
    """
    count = DynamicSession.query.filter_by(
        user_id=current_user.id,
        course='alphabets_ai'
    ).filter(DynamicSession.completed_at.isnot(None)).count()

    return jsonify({'count': count})


@views_ai.route('/api/ai/session/start', methods=['POST'])
@login_required
def start_ai_session():
    """
    Generate and start a personalized 15-sign session.
    """
    # Generate the plan
    plan = AIDifficultyEngine.generate_session_plan(current_user.id)

    # Create a new DynamicSession to track this (reusing the model)
    session = DynamicSession(
        user_id=current_user.id,
        course='alphabets_ai',  # Distinguish from standard dynamic
        mode='ai',
        total_signs=len(plan),
        correct_count=0,
        incorrect_count=0
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        'session_id': session.id,
        'plan': plan
    })


@views_ai.route('/api/ai/session/validate', methods=['POST'])
@login_required
def validate_ai_sign():
    """
    Validate a sign attempt against AI-calculated threshold.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    sign_id = data.get('sign_id')
    detected_sign = data.get('detected_sign')
    confidence = float(data.get('confidence', 0))
    threshold = float(data.get('threshold', 60))

    # Validation: Only check if sign matches (like static difficulty)
    # Confidence threshold is used for tracking only, not for pass/fail
    is_correct = (detected_sign == sign_id)

    # Update Stats immediately (for real-time adaptation if needed, though usually batch)
    # The requirement says "After every Dynamic or AI session", but also "Update UserSignStats [after session ends]".
    # However, "Update Triggers: After every Dynamic or AI session" usually implies bulk, but
    # "SignAttempt.create" happens during session.
    # We'll log the attempt now.

    attempt = SignAttempt(
        session_id=session_id,
        user_id=current_user.id,
        sign_id=sign_id,
        course='alphabets_ai',
        was_correct=is_correct,
        ai_detected_sign=detected_sign,
        ai_confidence=confidence,
        validation_threshold=threshold,
        study_time_used=data.get('study_time'),
        attempted_at=datetime.now()
    )
    db.session.add(attempt)
    db.session.commit()

    # ===== GAMIFICATION: Sign EXP (AI mode) =====
    gami_data = {}
    try:
        up = gami.get_or_create_user_progress(current_user.id)
        up.total_signs_attempted += 1
        if is_correct:
            up.total_signs_correct += 1
        db.session.commit()

        sign_gami = gami.calculate_sign_exp(
            user_id=current_user.id,
            session_id=session_id,
            attempt_id=attempt.id,
            was_correct=is_correct,
            ai_confidence=confidence / 100.0
        )
        sign_ach = gami.check_sign_achievements(
            current_user.id, is_correct, confidence / 100.0)
        gami_data = {
            'sign_exp': sign_gami['exp'],
            'sign_bonuses': sign_gami['bonuses'],
            'level_data': sign_gami['level_data'],
            'new_achievements': sign_ach,
        }
    except Exception as ge:
        print(f"⚠️ Gamification error (sign AI): {ge}")
    # ===== END GAMIFICATION =====

    return jsonify({
        'is_correct': is_correct,
        'detected': detected_sign,
        'confidence': confidence,
        'threshold': threshold,
        'gamification': gami_data,
    })


@views_ai.route('/api/ai/session/complete', methods=['POST'])
@login_required
def complete_ai_session():
    """
    Finalize the session and update aggregate stats with detailed breakdown.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    tier_map = data.get('tier_map', {})  # Receive tier info from frontend

    session = DynamicSession.query.get(session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({'error': 'Session not found'}), 404

    session.completed_at = datetime.now()

    # Calculate stats based on stored attempts
    attempts = SignAttempt.query.filter_by(session_id=session_id).all()
    correct_count = sum(1 for a in attempts if a.was_correct)

    session.correct_count = correct_count
    session.incorrect_count = len(attempts) - correct_count

    # Update UserSignStats for each sign practiced
    from collections import defaultdict
    sign_attempts_map = defaultdict(list)
    for att in attempts:
        sign_attempts_map[att.sign_id].append(att)

    for sign_id, atts in sign_attempts_map.items():
        for att in atts:
            AIDifficultyEngine.update_stats_after_attempt(
                current_user.id,
                sign_id,
                att.was_correct,
                att.ai_confidence
            )

    db.session.commit()

    # Generate detailed performance breakdown using tier_map from frontend
    all_stats = AIDifficultyEngine.get_user_stats(current_user.id)
    stats_map = {s.sign_id: s for s in all_stats}

    # Categorize signs from this session using the tier_map
    challenging_signs = []
    moderate_signs = []
    easy_signs = []

    for sign_id, atts in sign_attempts_map.items():
        stats = stats_map.get(sign_id)
        original_tier = tier_map.get(
            sign_id, 'Moderate')  # Use tier from frontend

        if stats:
            metrics = AIDifficultyEngine.calculate_sign_metrics(stats)
            was_correct = any(a.was_correct for a in atts)

            sign_info = {
                'sign': sign_id,
                'was_correct': was_correct,
                'accuracy': f"{(stats.correct_count / stats.total_attempts * 100):.0f}%",
                'confidence': f"{stats.avg_confidence:.0f}%",
                'total_attempts': stats.total_attempts,
                'difficulty': original_tier,
                'predicted_success': f"{(metrics['predicted_success'] * 100):.0f}%"
            }

            # Categorize by tier from frontend
            if original_tier == 'Challenging':
                challenging_signs.append(sign_info)
            elif original_tier == 'Moderate':
                moderate_signs.append(sign_info)
            else:
                easy_signs.append(sign_info)

    report = {
        'total_correct': correct_count,
        'total_signs': len(attempts),
        'session_breakdown': {
            'challenging': challenging_signs,
            'moderate': moderate_signs,
            'easy': easy_signs
        }
    }

    # ===== GAMIFICATION: Session complete (AI mode) =====
    try:
        streak_data = gami.update_streak(current_user.id)

        sess_gami = gami.calculate_session_exp(
            user_id=current_user.id,
            session_id=session_id,
            correct_count=correct_count,
            total_signs=len(attempts)
        )
        sess_ach = gami.check_session_achievements(
            user_id=current_user.id,
            session_id=session_id,
            correct_count=correct_count,
            total_signs=len(attempts),
            mode='ai'
        )
        report['gamification'] = {
            'session_exp': sess_gami['exp'],
            'session_bonuses': sess_gami['bonuses'],
            'level_data': sess_gami['level_data'],
            'streak': streak_data,
            'new_achievements': sess_ach,
        }
    except Exception as ge:
        import traceback
        print(f"⚠️ Gamification error (session AI): {ge}")
        print(traceback.format_exc())
    # ===== END GAMIFICATION =====

    return jsonify(report)
