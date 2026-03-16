from website import create_app, db
from website.models import User, DynamicSession
from website.ai_logic import AIDifficultyEngine
from flask_login import login_user
import sys

app = create_app()

def debug_session_start():
    with app.app_context():
        # Get a user (first user)
        user = User.query.first()
        if not user:
            print("No user found!")
            return

        print(f"Testing with user: {user.first_name} (ID: {user.id})")
        
        try:
            print("1. Testing Session Plan Generation...")
            plan = AIDifficultyEngine.generate_session_plan(user.id)
            print(f"[SUCCESS] Plan generated with {len(plan)} signs.")
            
            print("2. Testing DB Session Creation...")
            session = DynamicSession(
                user_id=user.id,
                course='alphabets_ai',
                total_signs=len(plan),
                correct_count=0,
                incorrect_count=0
            )
            db.session.add(session)
            db.session.commit()
            print(f"[SUCCESS] Session created. ID: {session.id}")
            
            # Clean up
            db.session.delete(session)
            db.session.commit()
            print("[SUCCESS] Test session cleaned up.")
            
        except Exception as e:
            import traceback
            print(f"[ERROR] ERROR: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    debug_session_start()
