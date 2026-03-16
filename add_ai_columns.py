from website import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking for missing AI columns in UserSignStats...")
    
    with db.engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("PRAGMA table_info(user_sign_stats);")).fetchall()
        columns = [row[1] for row in result]
        
        if 'avg_confidence' not in columns:
            print("Adding avg_confidence column...")
            try:
                conn.execute(text("ALTER TABLE user_sign_stats ADD COLUMN avg_confidence FLOAT DEFAULT 0.0"))
                print("[SUCCESS] avg_confidence added.")
            except Exception as e:
                print(f"[ERROR] Error adding avg_confidence: {e}")

        if 'last_5_attempts' not in columns:
            print("Adding last_5_attempts column...")
            try:
                conn.execute(text("ALTER TABLE user_sign_stats ADD COLUMN last_5_attempts TEXT DEFAULT '[]'"))
                print("[SUCCESS] last_5_attempts added.")
            except Exception as e:
                print(f"[ERROR] Error adding last_5_attempts: {e}")
                
        if 'avg_confidence' in columns and 'last_5_attempts' in columns:
            print("All columns already exist.")
            
    print("Database update complete.")
