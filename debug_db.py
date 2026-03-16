import sqlite3
import os
import requests

db_path = os.path.join('instance', 'database.db')

def check_db():
    print(f"Checking database at {db_path}...")
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables found: {tables}")
        
        if 'dynamic_session' in tables:
            print("✅ 'dynamic_session' table exists.")
        else:
            print("❌ 'dynamic_session' table MISSING.")

        if 'user' in tables:
            cursor.execute("PRAGMA table_info(user)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'dynamic_alphabets_unlocked' in columns:
                print("✅ User columns for dynamic unlock exist.")
            else:
                print("❌ User columns for dynamic unlock MISSING.")
        
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_db()
