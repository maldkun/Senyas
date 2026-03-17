"""
Backfill script: Populate ai_sign_stats from existing SignAttempt records.

This reads historical sign attempts from sessions that were run in 'ai' mode
and aggregates them into the ai_sign_stats table.

Safe to run multiple times (idempotent — updates existing rows, inserts missing ones).
Does NOT touch sign detection, gamification, or any other feature.

Usage:
  python backfill_ai_sign_stats.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from website import create_app, db
from website.models import SignAttempt, DynamicSession, AISignStats
from sqlalchemy import func

app = create_app()


def compute_difficulty(total_attempts, correct_count):
    """
    Compute difficulty score: 0.0 (always correct) → 1.0 (always wrong).
    Returns 0.5 if no attempts.
    """
    if total_attempts == 0:
        return 0.5
    error_rate = 1.0 - (correct_count / total_attempts)
    # Clamp to 0.0–1.0
    return round(max(0.0, min(1.0, error_rate)), 4)


def compute_confidence_patterns(attempts):
    """Build confidence-related aggregates from a list of attempt objects."""
    confidences = [a.ai_confidence for a in attempts if a.ai_confidence is not None]
    if not confidences:
        return {}
    avg = sum(confidences) / len(confidences)
    best = max(confidences)
    # Simple trend: compare avg of first half vs second half
    half = len(confidences) // 2
    if half > 0:
        first_avg = sum(confidences[:half]) / half
        second_avg = sum(confidences[half:]) / (len(confidences) - half)
        trend = "improving" if second_avg > first_avg + 0.02 else (
            "declining" if second_avg < first_avg - 0.02 else "stable"
        )
    else:
        trend = "stable"
    return {
        "avg_confidence": round(avg, 4),
        "best_confidence": round(best, 4),
        "trend": trend,
        "sample_count": len(confidences)
    }


def compute_study_time_prefs(attempts):
    """Aggregate study time data from attempts."""
    times = [a.study_time_used for a in attempts
             if a.study_time_used is not None and a.study_time_used > 0]
    correct_times = [a.study_time_used for a in attempts
                     if a.was_correct and a.study_time_used is not None and a.study_time_used > 0]
    if not times:
        return {}
    avg_time = sum(times) / len(times)
    best_success_time = min(correct_times) if correct_times else None
    return {
        "avg_time_seconds": round(avg_time, 2),
        "best_success_time": round(best_success_time, 2) if best_success_time else None,
        "total_time_seconds": sum(times),
        "sample_count": len(times)
    }


def build_performance_history(attempts, max_entries=50):
    """Build a JSON-serializable performance history list from attempts."""
    history = []
    for a in attempts[-max_entries:]:  # Keep most recent N
        entry = {
            "date": a.attempted_at.strftime("%Y-%m-%d") if a.attempted_at else None,
            "was_correct": bool(a.was_correct),
            "confidence": round(a.ai_confidence, 4) if a.ai_confidence is not None else None,
            "threshold": a.validation_threshold
        }
        history.append(entry)
    return history


def build_last_5(attempts):
    """Build JSON list of last 5 boolean results."""
    last_5 = [bool(a.was_correct) for a in attempts[-5:]]
    return json.dumps(last_5)


def backfill():
    with app.app_context():
        print("\n🔍 Scanning existing sign attempts for AI-mode sessions...\n")

        # Find all AI-mode sessions
        ai_sessions = DynamicSession.query.filter(
            DynamicSession.mode == 'ai'
        ).all()

        print(f"  Found {len(ai_sessions)} AI session(s).\n")

        if not ai_sessions:
            print("  No AI sessions found. Nothing to backfill.")
            print("  Note: ai_sign_stats will populate naturally as users play AI mode.")
            return

        # Collect all attempt records from those sessions
        ai_session_ids = [s.id for s in ai_sessions]
        all_attempts = SignAttempt.query.filter(
            SignAttempt.session_id.in_(ai_session_ids)
        ).order_by(SignAttempt.attempted_at.asc()).all()

        print(f"  Found {len(all_attempts)} total sign attempt(s) across AI sessions.\n")

        if not all_attempts:
            print("  No attempts found in AI sessions. Nothing to backfill.")
            return

        # Group attempts by (user_id, sign_id, course)
        grouped = {}
        for attempt in all_attempts:
            # Determine course key: use 'alphabets_ai' for alphabets AI sessions
            course = attempt.course or 'alphabets'
            ai_course = f"{course}_ai" if not course.endswith('_ai') else course
            key = (attempt.user_id, attempt.sign_id, ai_course)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(attempt)

        print(f"  Found {len(grouped)} unique (user, sign, course) combinations to backfill.\n")

        inserted = 0
        updated = 0

        for (user_id, sign_id, ai_course), attempts in grouped.items():
            total = len(attempts)
            correct = sum(1 for a in attempts if a.was_correct)
            last_practiced = max(
                (a.attempted_at for a in attempts if a.attempted_at),
                default=None
            )
            confidences = [a.ai_confidence for a in attempts if a.ai_confidence is not None]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            last_5 = build_last_5(attempts)
            difficulty = compute_difficulty(total, correct)
            perf_history = json.dumps(build_performance_history(attempts))
            study_time = json.dumps(compute_study_time_prefs(attempts))

            # Build threshold history from attempts
            threshold_history = []
            seen_sessions = set()
            for a in attempts:
                if a.session_id and a.session_id not in seen_sessions:
                    seen_sessions.add(a.session_id)
                    threshold_history.append({
                        "session_id": a.session_id,
                        "threshold": a.validation_threshold
                    })
            ai_threshold_history = json.dumps(threshold_history)

            # Check if row already exists
            existing = AISignStats.query.filter_by(
                user_id=user_id,
                sign_id=sign_id,
                course=ai_course
            ).first()

            if existing:
                # Update with aggregated data
                existing.total_attempts = total
                existing.correct_count = correct
                existing.last_practiced_at = last_practiced
                existing.avg_confidence = round(avg_conf, 4)
                existing.last_5_attempts = last_5
                existing.ai_difficulty_score = difficulty
                existing.ai_threshold_history = ai_threshold_history
                existing.performance_history = perf_history
                existing.study_time_prefs = study_time
                updated += 1
                print(f"  📝 Updated: user={user_id} sign={sign_id} course={ai_course} "
                      f"attempts={total} correct={correct}")
            else:
                # Insert new row
                row = AISignStats(
                    user_id=user_id,
                    sign_id=sign_id,
                    course=ai_course,
                    total_attempts=total,
                    correct_count=correct,
                    last_practiced_at=last_practiced,
                    avg_confidence=round(avg_conf, 4),
                    last_5_attempts=last_5,
                    ai_difficulty_score=difficulty,
                    ai_threshold_history=ai_threshold_history,
                    performance_history=perf_history,
                    study_time_prefs=study_time
                )
                db.session.add(row)
                inserted += 1
                print(f"  ➕ Inserted: user={user_id} sign={sign_id} course={ai_course} "
                      f"attempts={total} correct={correct}")

        db.session.commit()
        print(f"\n🎉 Backfill complete! Inserted: {inserted}, Updated: {updated}")
        print(f"   Total rows in ai_sign_stats: {AISignStats.query.count()}")


if __name__ == '__main__':
    try:
        backfill()
    except Exception as e:
        import traceback
        print(f"\n❌ Backfill failed: {e}")
        traceback.print_exc()
        sys.exit(1)
