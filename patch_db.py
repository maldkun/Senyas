import sqlite3
import os

DB_NAME = "instance/database.db"

def patch_database():
    if not os.path.exists(DB_NAME):
        print(f"DATABASE NOT FOUND: {DB_NAME}")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Add the fsl_progress column if it doesn't exist
        print("Checking if 'fsl_progress' column exists...")
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'fsl_progress' not in columns:
            print("Adding 'fsl_progress' column to 'user' table...")
            cursor.execute("ALTER TABLE user ADD COLUMN fsl_progress INTEGER DEFAULT 0")
            conn.commit()
            print("DB patched successfully!")
        else:
            print("fsl_progress column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error patching database: {e}")

if __name__ == "__main__":
    patch_database()
