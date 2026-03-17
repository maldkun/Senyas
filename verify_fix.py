
import os
from flask import Flask, render_template
from website import create_app, db
from website.models import User, UserSignStats

app = create_app()

def verify_render(template_name):
    print(f"Verifying {template_name}...")
    with app.test_request_context('/progress'):
        stats = [
            UserSignStats(sign_id='A', total_attempts=0, correct_count=0),
            UserSignStats(sign_id='B', total_attempts=1, correct_count=1)
        ]
        try:
            html = render_template(
                template_name,
                course='alphabets',
                stats=stats,
                sessions=[],
                total_practiced=1,
                recent_success_rate=100,
                current_study_time=5,
                current_threshold=70
            )
            print(f"  ✅ {template_name} rendered successfully.")
            # Basic check if success rate for 'A' is shown as 0% (default when not practiced)
            if 'A' in html and '0%' in html:
                 print(f"  ✅ {template_name} contains expected 0% for unpracticed sign.")
        except Exception as e:
            print(f"  ❌ {template_name} failed: {type(e).__name__}: {str(e)}")
            return False
    return True

if __name__ == "__main__":
    v1 = verify_render("progress.html")
    v2 = verify_render("dynamicprogress.html")
    
    if v1 and v2:
        print("\nAll verifications passed!")
    else:
        print("\nSome verifications failed.")
        exit(1)
