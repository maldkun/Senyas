
import os
from flask import Flask, render_template, request
from website import create_app, db
from website.models import User, UserSignStats, DynamicSession, SignAttempt
from sqlalchemy import func

app = create_app()

@app.route('/test_progress')
def test_progress():
    # Mock data that would cause ZeroDivisionError
    course = 'alphabets'
    stats = [
        UserSignStats(sign_id='A', total_attempts=0, correct_count=0),
        UserSignStats(sign_id='B', total_attempts=1, correct_count=1)
    ]
    sessions = []
    total_practiced = 0
    recent_success_rate = 0
    current_study_time = 5
    current_threshold = 70
    
    try:
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
    except Exception as e:
        return f"Caught expected error: {type(e).__name__}: {str(e)}", 500

if __name__ == "__main__":
    # We just want to see if it renders or crashes
    with app.app_context():
        course = 'alphabets'
        stats = [
            UserSignStats(sign_id='A', total_attempts=0, correct_count=0),
            UserSignStats(sign_id='B', total_attempts=1, correct_count=1)
        ]
        sessions = []
        total_practiced = 1
        recent_success_rate = 100
        current_study_time = 5
        current_threshold = 70
        
        try:
            html = render_template(
                "progress.html",
                course=course,
                stats=stats,
                sessions=sessions,
                total_practiced=total_practiced,
                recent_success_rate=recent_success_rate,
                current_study_time=current_study_time,
                current_threshold=current_threshold
            )
            print("Rendered successfully (unexpected if bug exists)")
        except Exception as e:
            print(f"Caught error: {type(e).__name__}: {str(e)}")
