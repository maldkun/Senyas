from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
from .models import db, Feedback, DynamicSession, SignAttempt, UserSignStats
from .models import UserProgress, Achievement, UserAchievement
from sqlalchemy import func
from . import gamification as gami
import json
import base64
import numpy as np
from io import BytesIO
import sys
import os

# Add parent directory and Sign Language model directory to path for importing FSL modules
def robust_fsl_import():
    """Robustly import FSL modules from multiple possible locations"""
    import sys
    import os
    
    # Potential paths to search
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    paths_to_try = [
        base_dir,
        os.path.join(base_dir, 'Sign Language model'),
        '/app',
        '/app/Sign Language model'
    ]
    
    # Try standard import first
    try:
        from fsl_inference import get_inference_engine, ProgressiveSignSequence
        return get_inference_engine, ProgressiveSignSequence
    except ImportError:
        pass

    # Try each path
    for p in paths_to_try:
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)
        try:
            from fsl_inference import get_inference_engine, ProgressiveSignSequence
            print(f"✅ Successfully imported FSL inference from: {p}")
            return get_inference_engine, ProgressiveSignSequence
        except ImportError:
            continue
            
    return None, None

get_inference_engine, ProgressiveSignSequence = robust_fsl_import()

if get_inference_engine is None:
    print("❌ FAILED TO LOAD FSL INFERENCE MODULE FROM ALL PATHS")

views = Blueprint('views', __name__)

# Global session for FSL sequences
fsl_sessions = {}


@views.route('/')
@login_required
def home():
    return render_template("home.html")


@views.route('/progress')
@login_required
def progress():
    course = request.args.get('course', 'alphabets')
    
    # Ensure all signs exist in stats for research clarity
    if course == 'alphabets':
        gami.ensure_all_stats_exist(current_user.id, course)

    # Get user's stats for this course
    stats = UserSignStats.query.filter_by(
        user_id=current_user.id,
        course=course
    ).all()

    # Get recent sessions
    sessions = DynamicSession.query.filter_by(
        user_id=current_user.id,
        course=course
    ).filter(DynamicSession.completed_at.isnot(None)).order_by(
        DynamicSession.completed_at.desc()
    ).limit(10).all()

    # Calculate summary stats
    total_practiced = sum(s.total_attempts for s in stats)

    # Get last 30 attempts for recent success rate
    recent_attempts = SignAttempt.query.filter_by(
        user_id=current_user.id,
        course=course
    ).order_by(SignAttempt.attempted_at.desc()).limit(30).all()

    recent_success_rate = 0
    if recent_attempts:
        recent_correct = sum(1 for a in recent_attempts if a.was_correct)
        recent_success_rate = round(
            (recent_correct / len(recent_attempts)) * 100, 1)

    # Get current settings from last session
    current_study_time = 5
    current_threshold = 70
    if sessions:
        current_study_time = sessions[0].final_study_time or 5
        current_threshold = sessions[0].final_threshold or 70

    return render_template(
        "progress.html",
        course=course,
        stats=stats,
        sessions=sessions,
        total_practiced=total_practiced,
        recent_success_rate=recent_success_rate,
        current_study_time=current_study_time,
        current_threshold=current_threshold
    )


@views.route('/leaderboard')
@login_required
def leaderboard():
    return render_template("leaderboard.html")


@views.route('/achievements')
@login_required
def achievements():
    return render_template("achievements.html")


# ============================================================================
# Gamification API Endpoints
# ============================================================================

@views.route('/api/gamification/progress')
@login_required
def gamification_progress():
    """Return current user's level, EXP, streak, and counters."""
    prog = gami.get_or_create_user_progress(current_user.id)
    return jsonify({
        "user_id":               current_user.id,
        "total_exp":             prog.total_exp,
        "current_level":         prog.current_level,
        "level_title":           gami.get_level_title(prog.current_level),
        "level_progress_percent": gami.get_level_progress_percent(prog.total_exp),
        "exp_to_next_level":     gami.get_exp_to_next_level(prog.total_exp),
        "is_max_level":          prog.current_level >= gami.MAX_LEVEL,
        "current_streak_days":   prog.current_streak_days,
        "longest_streak_days":   prog.longest_streak_days,
        "streak_bonus":          gami.calculate_streak_bonus(prog.current_streak_days),
        "total_sessions_completed": prog.total_sessions_completed,
        "total_signs_attempted": prog.total_signs_attempted,
        "total_signs_correct":   prog.total_signs_correct,
    }), 200


@views.route('/api/gamification/achievements')
@login_required
def gamification_achievements():
    """Return all achievements with per-user unlock status."""
    all_achs = Achievement.query.order_by(Achievement.sort_order).all()
    unlocked_ids = {
        ua.achievement_id: ua.unlocked_at
        for ua in UserAchievement.query.filter_by(user_id=current_user.id).all()
    }

    result = []
    by_category = {}
    for ach in all_achs:
        is_unlocked = ach.id in unlocked_ids
        item = {
            "id":           ach.id,
            "key":          ach.achievement_key,
            "name":         ach.name,
            "description":  ach.description,
            "category":     ach.category,
            "badge_icon":   ach.badge_icon,
            "exp_reward":   ach.exp_reward,
            "is_hidden":    ach.is_hidden,
            "is_unlocked":  is_unlocked,
            "unlocked_at":  unlocked_ids[ach.id].isoformat() if is_unlocked else None,
        }
        result.append(item)
        by_category.setdefault(ach.category, []).append(item)

    unlocked_count = sum(1 for i in result if i["is_unlocked"])
    return jsonify({
        "total_count":    len(result),
        "unlocked_count": unlocked_count,
        "achievements":   result,
        "by_category":    by_category,
    }), 200


@views.route('/api/gamification/exp-history')
@login_required
def gamification_exp_history():
    """Return last N EXP transactions for the current user."""
    from .models import EXPTransaction
    limit = int(request.args.get('limit', 50))
    txs = EXPTransaction.query.filter_by(user_id=current_user.id).order_by(
        EXPTransaction.created_at.desc()
    ).limit(limit).all()
    return jsonify({
        "transactions": [{
            "id":          t.id,
            "exp_amount":  t.exp_amount,
            "exp_source":  t.exp_source,
            "description": t.description,
            "created_at":  t.created_at.isoformat() if t.created_at else None,
        } for t in txs]
    }), 200


@views.route('/api/gamification/showcase-achievement', methods=['POST'])
@login_required
def showcase_achievement():
    data = request.get_json()
    achievement_id = data.get('achievement_id')
    showcase = data.get('showcase', True)
    ua = UserAchievement.query.filter_by(
        user_id=current_user.id, achievement_id=achievement_id
    ).first()
    if not ua:
        return jsonify({'success': False, 'message': 'Achievement not found'}), 404
    ua.is_showcased = showcase
    db.session.commit()
    return jsonify({'success': True, 'message': 'Showcase updated'}), 200


@views.route('/friends')
@login_required
def friends():
    return render_template("friends.html")


@views.route('/settings')
@login_required
def settings():
    return render_template("settings.html")


@views.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        feedback_text = request.form.get('feedback')

        if not feedback_text or len(feedback_text.strip()) < 1:
            flash('Feedback cannot be empty!', category='error')
        else:
            new_feedback = Feedback(
                user_id=current_user.id, data=feedback_text)
            db.session.add(new_feedback)
            db.session.commit()
            return redirect(url_for('views.feedback'))

    feedbacks = Feedback.query.all()
    return render_template("feedback.html", user=current_user, feedbacks=feedbacks)


@views.route('/delete-feedback/<int:id>')
@login_required
def delete_feedback(id):
    feedback = Feedback.query.get(id)
    if feedback:
        if feedback.user_id == current_user.id:
            db.session.delete(feedback)
            db.session.commit()
        else:
            flash('You can only delete your own feedback!', category='error')
    else:
        flash('Feedback not found!', category='error')
    return redirect(url_for('views.feedback'))


@views.route('/coursealphabets')
@login_required
def coursealphabets():
    return render_template("coursealphabets.html", fsl_progress=current_user.fsl_progress)


# ============================================================================
# FSL (Filipino Sign Language) Endpoints for Real-time Recognition
# ============================================================================

@views.route('/api/fsl/debug')
def fsl_debug():
    """Diagnostic endpoint to check FSL environment"""
    import os
    import sys
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    fsl_path = os.path.join(base_dir, 'Sign Language model')
    model_dir = os.path.join(fsl_path, 'models')
    
    dep_report = {}
    for mod in ['numpy', 'tensorflow', 'mediapipe', 'cv2']:
        try:
            m = __import__(mod)
            dep_report[mod] = f"OK ({getattr(m, '__version__', 'unknown')})"
        except Exception as e:
            dep_report[mod] = f"ERROR: {str(e)}"

    return jsonify({
        'cwd': os.getcwd(),
        'base_dir': base_dir,
        'fsl_dir': fsl_path,
        'fsl_dir_exists': os.path.exists(fsl_path),
        'model_dir_exists': os.path.exists(model_dir),
        'fsl_module_loaded': get_inference_engine is not None,
        'sys_path': sys.path,
        'dependencies': dep_report
    })

@views.route('/api/fsl/predict', methods=['POST'])
@login_required
def fsl_predict():
    """
    Predict FSL sign from landmark data

    POST data:
        landmarks: list of 63 floats (21 landmarks × 3 coordinates)
        session_id: optional session identifier
        smooth: bool to use smoothing (default: true)

    Returns:
        {
            'sign': str or null,
            'confidence': float,
            'threshold_met': bool
        }
    """
    try:
        if get_inference_engine is None:
            return jsonify({'error': 'FSL module not available'}), 500

        data = request.get_json()

        if not data or 'landmarks' not in data:
            return jsonify({'error': 'Missing landmarks data'}), 400

        landmarks = np.array(data['landmarks'], dtype=np.float32)
        session_id = data.get('session_id', str(current_user.id))
        use_smoothing = data.get('smooth', True)

        engine = get_inference_engine()

        if use_smoothing:
            result = engine.get_smoothed_prediction(landmarks, session_id)
        else:
            result = engine.predict_sign(landmarks)

        def convert_numpy(obj):
            if isinstance(obj, dict):
                return {str(k): convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(i) for i in obj]
            elif hasattr(obj, 'item'):
                return obj.item()
            return obj

        return jsonify(convert_numpy(result)), 200

    except Exception as e:
        import traceback
        err_msg = f"❌ FSL predict error: {str(e)}"
        print(err_msg)
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc() if os.environ.get('DEBUG') == 'true' else 'Check logs'
        }), 500


@views.route('/api/fsl/sequence/start', methods=['POST'])
@login_required
def fsl_sequence_start():
    """
    Start a new FSL learning sequence (Part-based)
    """
    try:
        data = request.get_json()
        part_idx = data.get('part', 1)

        # Define the 5 parts
        parts = {
            1: list("ABCDE"),
            2: list("FGHIJ"),
            3: list("KLMNO"),
            4: list("PQRST"),
            5: list("UVWXYZ")
        }

        if part_idx not in parts:
            return jsonify({'error': 'Invalid part index'}), 400

        # Check if part is unlocked
        if part_idx > current_user.fsl_progress + 1:
            return jsonify({'error': f'Part {part_idx} is locked'}), 403

        signs = parts[part_idx]

        # Create a new DynamicSession for this static part
        session = DynamicSession(
            user_id=current_user.id,
            course='alphabets',
            mode='static',
            total_signs=len(signs),
            correct_count=0,
            incorrect_count=0,
            final_study_time=0,
            final_threshold=50,
            sequence_data=json.dumps(signs),
            current_index=0
        )
        db.session.add(session)
        db.session.commit()

        session_id = session.id

        # Return identical payload as before
        current_target = signs[0] if signs else None
        
        return jsonify({
            'session_id': session_id,
            'sequence': signs,
            'target': current_target,
            'completed': [],
            'progress_percent': 0,
            'part': part_idx
        }), 200

    except Exception as e:
        print(f"FSL sequence start error: {e}")
        return jsonify({'error': str(e)}), 500


@views.route('/api/fsl/sequence/check', methods=['POST'])
@login_required
def fsl_sequence_check():
    """
    Check detected sign against current sequence target
    """
    # print(f"👉 STATIC CHECK REQUEST: {request.get_json()}")
    try:
        data = request.get_json()
        session_id = data.get('session_id', str(current_user.id))

        # Clean the input
        detected_sign = str(data.get('sign', '')).strip().upper()
        confidence = float(data.get('confidence', 0))
        part_idx = data.get('part')

        print(
            f"👉 CHECK: Session={session_id}, Sign='{detected_sign}', Conf={confidence}")

        session = DynamicSession.query.get(session_id)
        if not session or not session.sequence_data:
            print(f"❌ Session {session_id} not found in DB")
            return jsonify({'error': 'Session not found. Start a sequence first.'}), 404

        # Reconstruct sequence state
        sequence_list = json.loads(session.sequence_data)
        current_index = session.current_index
        
        current_target = sequence_list[current_index] if current_index < len(sequence_list) else None

        # === EXPLICIT VALIDATION (Ported from Dynamic Mode) ===
        # Simple, direct comparison without hidden state
        target_str = str(current_target).strip().upper() if current_target else ""

        print(f"👉 TARGET: '{target_str}' vs DETECTED: '{detected_sign}'")

        is_correct = (detected_sign == target_str and confidence >= 0.5)

        result = {
            'is_correct': is_correct,
            'target': current_target,
            'detected': detected_sign,
            'confidence': confidence,
            'message': 'Keep going'
        }

        if is_correct:
            print("✅ CORRECT! Advancing...")
            # Advance sequence manually in DB
            session.current_index += 1
            current_index = session.current_index
            db.session.commit()
            
            result['message'] = "Correct!"

            # Log the successful attempt exactly once per completed sign
            db_session_id = session.id
            if db_session_id and current_target:
                try:
                    attempt = SignAttempt(
                        session_id=db_session_id,
                        user_id=current_user.id,
                        sign_id=target_str,
                        course='alphabets',
                        was_correct=True,
                        ai_detected_sign=detected_sign,
                        ai_confidence=confidence,
                        validation_threshold=50,
                        study_time_used=0
                    )
                    db.session.add(attempt)

                    # Update session stats
                    sess = DynamicSession.query.get(db_session_id)
                    if sess:
                        sess.correct_count += 1

                    # Update UserSignStats
                    stats = UserSignStats.query.filter_by(
                        user_id=current_user.id,
                        sign_id=target_str,
                        course='alphabets'
                    ).first()

                    if stats:
                        stats.total_attempts += 1
                        stats.correct_count += 1
                        stats.last_practiced_at = func.now()
                    else:
                        stats = UserSignStats(
                            user_id=current_user.id,
                            sign_id=target_str,
                            course='alphabets',
                            total_attempts=1,
                            correct_count=1,
                            last_practiced_at=func.now()
                        )
                        db.session.add(stats)

                    db.session.commit()

                    # ===== GAMIFICATION: Sign EXP =====
                    try:
                        # Update UserProgress sign counters first
                        up = gami.get_or_create_user_progress(current_user.id)
                        up.total_signs_attempted += 1
                        up.total_signs_correct += 1
                        db.session.commit()

                        sign_gami = gami.calculate_sign_exp(
                            user_id=current_user.id,
                            session_id=db_session_id,
                            attempt_id=attempt.id,
                            was_correct=True,
                            ai_confidence=confidence
                        )
                        sign_ach = gami.check_sign_achievements(
                            current_user.id, True, confidence
                        )
                        result['gamification'] = {
                            'sign_exp': sign_gami['exp'],
                            'sign_bonuses': sign_gami['bonuses'],
                            'level_data': sign_gami['level_data'],
                            'new_achievements': sign_ach,
                        }
                    except Exception as ge:
                        print(f"⚠️ Gamification error (sign): {ge}")
                    # ===== END GAMIFICATION =====

                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Error saving static attempt: {e}")

            # Check for completion of part
            is_complete = current_index >= len(sequence_list)
            completed_signs = sequence_list[:current_index]
            progress_pct = int((current_index / len(sequence_list)) * 100) if sequence_list else 0
            new_target = sequence_list[current_index] if not is_complete else None

            # Mark session complete if done
            if is_complete and db_session_id:
                try:
                    sess = DynamicSession.query.get(db_session_id)
                    if sess:
                        sess.completed_at = func.now()
                        db.session.commit()
                    # ===== GAMIFICATION: Session complete (static) =====
                    try:
                        streak_data = gami.update_streak(current_user.id)
                        sess_reloaded = DynamicSession.query.get(db_session_id)
                        total_s = sess_reloaded.total_signs if sess_reloaded else 5
                        correct_s = sess_reloaded.correct_count if sess_reloaded else 0
                        sess_gami = gami.calculate_session_exp(
                            user_id=current_user.id,
                            session_id=db_session_id,
                            correct_count=correct_s,
                            total_signs=total_s
                        )
                        sess_ach = gami.check_session_achievements(
                            user_id=current_user.id,
                            session_id=db_session_id,
                            correct_count=correct_s,
                            total_signs=total_s,
                            mode='static'
                        )
                        result['session_gamification'] = {
                            'session_exp': sess_gami['exp'],
                            'session_bonuses': sess_gami['bonuses'],
                            'level_data': sess_gami['level_data'],
                            'streak': streak_data,
                            'new_achievements': sess_ach,
                        }
                    except Exception as ge:
                        print(f"⚠️ Gamification error (session): {ge}")
                    # ===== END GAMIFICATION =====
                except Exception as e:
                    db.session.rollback()

            result.update({
                'is_complete': is_complete,
                'completed': completed_signs,
                'sequence': sequence_list,
                'progress_percent': progress_pct,
                'target': new_target  # Next target
            })

            # If sequence is complete, update user progress
            if result.get('is_complete') and part_idx:
                try:
                    part_idx_int = int(part_idx)
                    if part_idx_int > current_user.fsl_progress:
                        current_user.fsl_progress = part_idx_int
                        db.session.commit()
                        result['new_overall_progress'] = current_user.fsl_progress
                except Exception as e:
                    print(f"Error updating progress: {e}")
        else:
            # Just return current status
            is_complete = current_index >= len(sequence_list)
            completed_signs = sequence_list[:current_index]
            progress_pct = int((current_index / len(sequence_list)) * 100) if sequence_list else 0
            
            result.update({
                'is_complete': is_complete,
                'completed': completed_signs,
                'progress_percent': progress_pct,
                'target': current_target
            })

        # Add debug info to response
        result['debug_info'] = {
            'detected_clean': detected_sign,
            'target_clean': target_str,
            'mode': 'DIRECT_VALIDATION_DB'
        }

        return jsonify(result), 200

    except Exception as e:
        import traceback
        print(f"❌ FSL sequence check error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/api/fsl/sequence/skip', methods=['POST'])
@login_required
def fsl_sequence_skip():
    """
    Skip the current sign in the sequence
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', str(current_user.id))
        print(f"👉 SKIP REQUEST: Session={session_id}")

        session = DynamicSession.query.get(session_id)
        if not session or not session.sequence_data:
            print(f"❌ Session {session_id} not found for skip")
            return jsonify({'error': 'Session not found. Start a sequence first.'}), 404

        sequence_list = json.loads(session.sequence_data)
        current_target = sequence_list[session.current_index] if session.current_index < len(sequence_list) else None

        # Advance it
        session.current_index += 1
        db.session.commit()
        
        current_index = session.current_index
        is_complete = current_index >= len(sequence_list)
        
        result = {
            'is_correct': True,
            'is_complete': is_complete,
            'message': f'⏹️ Skipped.',
            'progress_percent': int((current_index / len(sequence_list)) * 100) if sequence_list else 100,
            'completed': sequence_list[:current_index],
            'target': sequence_list[current_index] if not is_complete else None,
            'consecutive_count': 0,
            'sequence': sequence_list
        }
        
        print(f"✅ SKIPPED. Result: {result}")

        # Log the skipped attempt
        db_session_id = session.id
        target_str = str(current_target).strip().upper() if current_target else ""
        
        if db_session_id and target_str:
            try:
                attempt = SignAttempt(
                    session_id=db_session_id,
                    user_id=current_user.id,
                    sign_id=target_str,
                    course='alphabets',
            mode='static',
                    was_correct=False,
                    ai_detected_sign='SKIPPED',
                    ai_confidence=0.0,
                    validation_threshold=50,
                    study_time_used=0
                )
                db.session.add(attempt)

                if session:
                    session.incorrect_count += 1
                    if is_complete:
                        session.completed_at = func.now()

                # Update UserSignStats for skipped attempt
                stats = UserSignStats.query.filter_by(
                    user_id=current_user.id,
                    sign_id=target_str,
                    course='alphabets'
                ).first()
                if stats:
                    stats.total_attempts += 1
                    stats.last_practiced_at = func.now()
                else:
                    stats = UserSignStats(
                        user_id=current_user.id,
                        sign_id=target_str,
                        course='alphabets',
                        total_attempts=1,
                        correct_count=0,
                        last_practiced_at=func.now()
                    )
                    db.session.add(stats)

                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error saving skipped attempt: {e}")

        return jsonify(result), 200

    except Exception as e:
        import traceback
        print(f"❌ FSL sequence skip error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/api/fsl/sequence/progress', methods=['GET'])
@login_required
def fsl_sequence_progress():
    """
    Get current sequence progress

    Query params:
        session_id: optional session identifier

    Returns:
        {
            'current_target': str,
            'completed': list,
            'progress_percent': int,
            'is_complete': bool,
            'sequence': list
        }
    """
    try:
        session_id = request.args.get('session_id', str(current_user.id))

        session = DynamicSession.query.get(session_id)
        if not session or not session.sequence_data:
            return jsonify({'error': 'Session not found'}), 404

        sequence_list = json.loads(session.sequence_data)
        current_index = session.current_index
        is_complete = current_index >= len(sequence_list)
        
        progress = {
            'current_target': sequence_list[current_index] if not is_complete else None,
            'completed': sequence_list[:current_index],
            'progress_percent': int((current_index / len(sequence_list)) * 100) if sequence_list else 100,
            'is_complete': is_complete,
            'sequence': sequence_list
        }

        return jsonify(progress), 200

    except Exception as e:
        import traceback
        print(f"❌ FSL progress error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/api/fsl/available-signs', methods=['GET'])
@login_required
def fsl_available_signs():
    """
    Get list of available FSL signs the model can recognize

    Returns:
        {
            'signs': list of str,
            'count': int
        }
    """
    try:
        if get_inference_engine is None:
            return jsonify({'error': 'FSL module not available'}), 500

        engine = get_inference_engine()
        signs = engine.get_available_signs()

        if hasattr(signs, 'tolist'):
            signs = signs.tolist()

        return jsonify({
            'signs': signs,
            'count': len(signs)
        }), 200

    except Exception as e:
        import traceback
        print(f"❌ FSL available signs error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/api/delete-progress', methods=['POST'])
@login_required
def delete_progress():
    """
    Delete user's progress after password verification
    """
    try:
        data = request.get_json()
        password = data.get('password')

        if not password:
            return jsonify({'error': 'Password is required'}), 400

        if not check_password_hash(current_user.password, password):
            return jsonify({'error': 'Incorrect password'}), 401

        # Reset progress
        current_user.fsl_progress = 0
        db.session.commit()

        return jsonify({'message': 'Progress deleted successfully'}), 200

    except Exception as e:
        print(f"❌ Delete progress error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Dynamic Difficulty Endpoints
# ============================================================================

@views.route('/coursedynamic/<course>')
@login_required
def coursedynamic(course):
    """
    Dynamic practice page for adaptive learning
    """
    # Verify course is valid
    if course not in ['alphabets', 'words', 'phrases']:
        flash('Invalid course', category='error')
        return redirect(url_for('views.home'))

    # Check if unlocked
    unlock_field = f'dynamic_{course}_unlocked'
    is_unlocked = getattr(current_user, unlock_field, False)

    if not is_unlocked:
        flash(
            f'Complete Static Difficulty for {course.title()} first!', category='warning')
        return redirect(url_for('views.home'))

    return render_template('coursedynamic.html', course=course)


@views.route('/dynamic/unlock/<course>', methods=['POST'])
@login_required
def dynamic_unlock(course):
    """
    Unlock Dynamic mode for a course after Static completion
    """
    try:
        if course not in ['alphabets', 'words', 'phrases']:
            return jsonify({'error': 'Invalid course'}), 400

        unlock_field = f'dynamic_{course}_unlocked'

        # Check if already unlocked
        if getattr(current_user, unlock_field, False):
            return jsonify({'message': 'Already unlocked', 'unlocked': True}), 200

        # Unlock the course
        setattr(current_user, unlock_field, True)
        db.session.commit()

        return jsonify({
            'message': f'Dynamic Practice unlocked for {course.title()}!',
            'unlocked': True
        }), 200

    except Exception as e:
        print(f"❌ Unlock error: {e}")
        return jsonify({'error': str(e)}), 500


@views.route('/dynamic/session/start', methods=['POST'])
@login_required
def dynamic_session_start():
    """
    Start a new Dynamic practice session
    """
    print(f"👉 SESSION START REQUEST RECEIVED")
    try:
        data = request.get_json()
        print(f"👉 Session Data: {data}")

        if not data:
            print("❌ No JSON data received")
            return jsonify({'error': 'No data provided'}), 400

        course = data.get('course', 'alphabets')
        print(f"👉 Course: {course}")

        # Create new session
        print(f"👉 Creating session for user {current_user.id}")
        session = DynamicSession(
            user_id=current_user.id,
            course=course,
            mode='dynamic',
            total_signs=15,
            correct_count=0,
            incorrect_count=0,
            final_study_time=5,  # Initial
            final_threshold=70    # Initial
        )

        print("👉 Adding session to DB...")
        db.session.add(session)
        db.session.commit()
        print(f"✅ Session created with ID: {session.id}")

        return jsonify({
            'session_id': session.id,
            'course': course,
            'initial_study_time': 5,
            'initial_threshold': 70,
            'signs_per_session': 15
        }), 200

    except Exception as e:
        import traceback
        print(f"❌ Session start error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/dynamic/session/validate', methods=['POST'])
@login_required
def dynamic_session_validate():
    """
    Validate a sign attempt and record it
    """
    print(f"👉 VALIDATION REQUEST RECEIVED")
    try:
        data = request.get_json()
        print(f"👉 Validation Data: {data}")

        session_id = data.get('session_id')
        sign_id = str(data.get('sign_id', '')).strip().upper()
        detected_sign = str(data.get('detected_sign', '')).strip().upper()
        confidence = float(data.get('confidence', 0))
        threshold = float(data.get('threshold', 70))
        study_time = data.get('study_time', 5)
        course = data.get('course', 'alphabets')

        print(
            f"👉 Comparing: Expected='{sign_id}' vs Detected='{detected_sign}'")
        print(f"👉 Confidence: {confidence} >= Threshold: {threshold}")

        # Validate
        is_correct = (detected_sign == sign_id and
                      confidence >= threshold)

        print(f"👉 Result: {'CORRECT' if is_correct else 'INCORRECT'}")

        # Record attempt
        attempt = SignAttempt(
            session_id=session_id,
            user_id=current_user.id,
            sign_id=sign_id,
            course=course,
            was_correct=is_correct,
            ai_detected_sign=detected_sign,
            ai_confidence=confidence,
            validation_threshold=threshold,

            study_time_used=study_time,
            study_time_limit=data.get('study_time_limit'),
            current_threshold=data.get('current_threshold'),
            # Batch tracking - use defaults if not provided
            batch_index=data.get('batch_index', None),
            batch_size=data.get('batch_size', None),
            study_order_index=data.get('study_order_index', None),
            performance_order_index=data.get('performance_order_index', None)
        )

        try:
            db.session.add(attempt)
            db.session.commit()
            print(f"✅ Attempt saved successfully")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving attempt: {e}")
            return jsonify({'error': 'Database error', 'details': str(e)}), 500

        # Update or create user sign stats
        stats = UserSignStats.query.filter_by(
            user_id=current_user.id,
            sign_id=sign_id,
            course=course
        ).first()

        if stats:
            stats.total_attempts += 1
            if is_correct:
                stats.correct_count += 1
            stats.last_practiced_at = func.now()
        else:
            stats = UserSignStats(
                user_id=current_user.id,
                sign_id=sign_id,
                course='alphabets' if course == 'alphabets' else course,
                total_attempts=1,
                correct_count=1 if is_correct else 0,
                last_practiced_at=func.now()
            )
            db.session.add(stats)

        try:
            db.session.commit()
            print(f"✅ Stats updated successfully")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Warning: Could not update stats: {e}")
            # Continue anyway - the attempt was saved

        # ===== GAMIFICATION: Sign EXP (dynamic) =====
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
                ai_confidence=confidence / 100.0  # normalize if needed
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
            print(f"⚠️ Gamification error (sign dynamic): {ge}")
        # ===== END GAMIFICATION =====

        return jsonify({
            'is_correct': is_correct,
            'detected': detected_sign,
            'expected': sign_id,
            'confidence': confidence,
            'threshold': threshold,
            'gamification': gami_data,
            'debug_info': {
                'expected_repr': repr(sign_id),
                'detected_repr': repr(detected_sign),
                'confidence': confidence,
                'threshold': threshold,
                'match': (detected_sign == sign_id)
            }
        }), 200

    except Exception as e:
        import traceback
        print(f"❌ Validation error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/dynamic/session/complete', methods=['POST'])
@login_required
def dynamic_session_complete():
    """
    Complete a Dynamic practice session
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        final_study_time = data.get('final_study_time', 5)
        final_threshold = data.get('final_threshold', 70)

        # Find and update session
        session = DynamicSession.query.get(session_id)
        if not session or session.user_id != current_user.id:
            return jsonify({'error': 'Session not found'}), 404

        # Calculate stats from attempts
        attempts = SignAttempt.query.filter_by(session_id=session_id).all()
        correct = sum(1 for a in attempts if a.was_correct)
        incorrect = len(attempts) - correct

        session.completed_at = func.now()
        session.total_signs = len(attempts)
        session.correct_count = correct
        session.incorrect_count = incorrect
        session.final_study_time = final_study_time
        session.final_threshold = final_threshold
        session.mode = 'dynamic'

        db.session.commit()

        # ===== GAMIFICATION: Session complete (dynamic) =====
        gami_session = {}
        try:
            streak_data = gami.update_streak(current_user.id)

            # Batch EXP for all 5 batches using attempt data
            batch_groups = {}
            for a in attempts:
                bi = a.batch_index if a.batch_index is not None else 0
                batch_groups.setdefault(bi, []).append(a)
            batch_total_exp = 0
            for bi, batcha in batch_groups.items():
                bc = sum(1 for a in batcha if a.was_correct)
                bt = len(batcha)
                b_result = gami.calculate_batch_exp(
                    user_id=current_user.id,
                    session_id=session_id,
                    correct_in_batch=bc,
                    total_in_batch=bt
                )
                batch_total_exp += b_result['exp']
                # Batch achievement check
                gami.check_batch_achievements(current_user.id, bc, bt)

            sess_gami = gami.calculate_session_exp(
                user_id=current_user.id,
                session_id=session_id,
                correct_count=correct,
                total_signs=len(attempts)
            )
            sess_ach = gami.check_session_achievements(
                user_id=current_user.id,
                session_id=session_id,
                correct_count=correct,
                total_signs=len(attempts),
                mode='dynamic'
            )
            gami_session = {
                'session_exp': sess_gami['exp'],
                'batch_exp': batch_total_exp,
                'session_bonuses': sess_gami['bonuses'],
                'level_data': sess_gami['level_data'],
                'streak': streak_data,
                'new_achievements': sess_ach,
            }
        except Exception as ge:
            import traceback
            print(f"⚠️ Gamification error (session dynamic): {ge}")
            print(traceback.format_exc())
        # ===== END GAMIFICATION =====

        return jsonify({
            'success': True,
            'total': len(attempts),
            'correct': correct,
            'incorrect': incorrect,
            'success_rate': round((correct / len(attempts) * 100) if attempts else 0, 1),
            'gamification': gami_session,
        }), 200

    except Exception as e:
        import traceback
        print(f"❌ Session complete error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/dynamic/session/history', methods=['GET'])
@login_required
def dynamic_session_history():
    """
    Get session history with attempts for progress display
    """
    try:
        course = request.args.get('course', 'alphabets')
        limit = int(request.args.get('limit', 10))

        # Get recent completed sessions
        sessions = DynamicSession.query.filter_by(
            user_id=current_user.id,
            course=course
        ).filter(DynamicSession.completed_at.isnot(None)).order_by(
            DynamicSession.completed_at.desc()
        ).limit(limit).all()

        result = []
        for sess in sessions:
            # Get all attempts for this session
            attempts = SignAttempt.query.filter_by(session_id=sess.id).all()

            result.append({
                'session_id': sess.id,
                'completed_at': sess.completed_at.isoformat() if sess.completed_at else None,
                'total_signs': sess.total_signs,
                'correct_count': sess.correct_count,
                'incorrect_count': sess.incorrect_count,
                'final_study_time': sess.final_study_time,
                'final_threshold': sess.final_threshold,
                'attempts': [{
                    'sign_id': att.sign_id,
                    'was_correct': att.was_correct,
                    'ai_detected_sign': att.ai_detected_sign,
                    'ai_confidence': att.ai_confidence,
                    'batch_index': att.batch_index,
                    'batch_size': att.batch_size,
                    'study_order_index': att.study_order_index,
                    'performance_order_index': att.performance_order_index,
                    'study_time_used': att.study_time_used,
                    'study_time_limit': att.study_time_limit,
                    'current_threshold': att.current_threshold
                } for att in attempts]
            })

        return jsonify({'sessions': result}), 200

    except Exception as e:
        print(f"[ERROR] Session history error: {e}")
        return jsonify({'error': str(e)}), 500


# Import the standalone route defined in views_delete_session.py


@views.route('/dynamic/queue/generate', methods=['POST'])
@login_required
def dynamic_queue_generate():
    """
    Generate personalized sign queue based on user performance
    """
    print(f"👉 QUEUE GENERATION REQUEST RECEIVED")
    try:
        data = request.get_json()
        print(f"👉 Queue Data: {data}")

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        course = data.get('course', 'alphabets')
        session_length = int(data.get('session_length', 15))

        print(f"👉 Course: {course}, Length: {session_length}")

        # Get all available signs for the course
        if course == 'alphabets':
            all_signs = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        elif course == 'words':
            all_signs = ['HELLO', 'THANK YOU', 'SORRY',
                         'PLEASE', 'YES', 'NO']  # Example
        elif course == 'phrases':
            all_signs = ['GOOD MORNING', 'HOW ARE YOU']  # Example
        else:
            return jsonify({'error': 'Invalid course'}), 400

        print(f"👉 All signs count: {len(all_signs)}")

        # Get user's performance stats
        try:
            stats = UserSignStats.query.filter_by(
                user_id=current_user.id,
                course=course
            ).all()
            print(f"👉 Found {len(stats)} stats records")
        except Exception as db_err:
            print(f"❌ Database error fetching stats: {db_err}")
            stats = []

        # If no history, return random selection
        if not stats:
            print("👉 No stats found, generating random queue")
            import random
            queue = random.sample(all_signs, min(
                session_length, len(all_signs)))
            print(f"✅ Generated random queue: {queue}")
            return jsonify({'queue': queue, 'method': 'random'}), 200

        # Build performance map
        perf_map = {}
        for stat in stats:
            success_rate = (stat.correct_count / stat.total_attempts *
                            100) if stat.total_attempts > 0 else 0
            perf_map[stat.sign_id] = {
                'success_rate': success_rate,
                'total_attempts': stat.total_attempts,
                'last_practiced': stat.last_practiced_at
            }

        # Categorize signs
        struggled = []  # < 60% success rate
        review = []     # >= 60% but not practiced in 3+ days

        from datetime import datetime, timedelta
        three_days_ago = datetime.now() - timedelta(days=3)

        for sign in all_signs:
            if sign in perf_map:
                rate = perf_map[sign]['success_rate']
                last_practice = perf_map[sign]['last_practiced']

                # Normalize timezone-aware back to naive for comparison with datetime.now()
                if last_practice and hasattr(last_practice, 'tzinfo') and last_practice.tzinfo:
                    last_practice = last_practice.replace(tzinfo=None)

                if rate < 60:
                    struggled.append((sign, rate))
                elif last_practice and last_practice < three_days_ago:
                    review.append(sign)

        # Sort struggled by success rate (worst first)
        struggled.sort(key=lambda x: x[1])

        # Build queue with weighted priorities
        queue = []

        # Priority 1: Struggled signs (70% of queue)
        # Priority 1: Struggled signs (Add ONCE only)
        for sign, rate in struggled:
            queue.append(sign)

        # Priority 2: Review signs
        queue.extend(review)

        # Remove duplicates
        queue = list(dict.fromkeys(queue))

        # Shuffle
        import random
        random.shuffle(queue)

        # Define fixed batch size
        batch_size = 3

        # Trim to session length
        queue = queue[:session_length]

        # Pad with UNIQUE signs if needed
        while len(queue) < session_length:
            available = [s for s in all_signs if s not in queue]
            if not available:
                break
            queue.append(random.choice(available))

        print(
            f"👉 Session Length: {len(queue)}, Fixed Batch Size: {batch_size}")

        return jsonify({
            'queue': queue,
            'method': 'personalized',
            'batch_size': batch_size,
            'struggled_count': len(struggled),
            'review_count': len(review)
        }), 200

    except Exception as e:
        import traceback
        print(f"❌ Queue generation error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@views.route('/dynamic/session/delete/<int:session_id>', methods=['DELETE'])
@login_required
def dynamic_session_delete(session_id):
    """
    Delete a dynamic practice session and all its attempts
    """
    try:
        # Get the session
        session = DynamicSession.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Security: ensure user owns this session
        if session.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete all associated sign attempts first
        SignAttempt.query.filter_by(session_id=session_id).delete()
        
        # Delete the session
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Session deleted successfully'}), 200
    
    except Exception as e:
        print(f"❌ Session delete error: {e}")
        return jsonify({'error': str(e)}), 500
