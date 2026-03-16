import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'database.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(sign_attempt)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'study_time_limit' not in columns:
            print("Adding study_time_limit column...")
            cursor.execute("ALTER TABLE sign_attempt ADD COLUMN study_time_limit FLOAT")
        else:
            print("study_time_limit column already exists.")

        if 'current_threshold' not in columns:
            print("Adding current_threshold column...")
            cursor.execute("ALTER TABLE sign_attempt ADD COLUMN current_threshold INTEGER")
        else:
            print("current_threshold column already exists.")
            
        conn.commit()
        print("Migration successful!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
