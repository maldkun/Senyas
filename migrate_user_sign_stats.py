"""
Migration script to fix user_sign_stats table
Adds missing id column and recreates the table with proper schema
"""

import sqlite3
import os

# Path to your database
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

print(f"Connecting to database: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if the table exists
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='user_sign_stats'")
    result = cursor.fetchone()
    
    if result:
        print("\n[*] Current user_sign_stats schema:")
        print(result[0])
        
        # Backup existing data
        print("\n[*] Backing up existing data...")
        cursor.execute("SELECT * FROM user_sign_stats")
        existing_data = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(user_sign_stats)")
        columns = cursor.fetchall()
        print(f"Found {len(existing_data)} rows with columns: {[col[1] for col in columns]}")
        
        # Drop the old table
        print("\n[*] Dropping old table...")
        cursor.execute("DROP TABLE user_sign_stats")
        
        # Create new table with correct schema
        print("\n[*] Creating new table with id column...")
        cursor.execute("""
            CREATE TABLE user_sign_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sign_id VARCHAR(50) NOT NULL,
                course VARCHAR(50) NOT NULL,
                total_attempts INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_practiced_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES user(id),
                UNIQUE (user_id, sign_id, course)
            )
        """)
        
        # Restore data (id will be auto-generated)
        if existing_data:
            print(f"\n[*] Restoring {len(existing_data)} rows...")
            # Assuming old schema was: user_id, sign_id, course, total_attempts, correct_count, last_practiced_at
            for row in existing_data:
                cursor.execute("""
                    INSERT INTO user_sign_stats (user_id, sign_id, course, total_attempts, correct_count, last_practiced_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, row)
        
        conn.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        
        # Verify
        cursor.execute("PRAGMA table_info(user_sign_stats)")
        new_columns = cursor.fetchall()
        print("\n[*] New schema:")
        for col in new_columns:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print("\n[!] user_sign_stats table does not exist, creating it...")
        cursor.execute("""
            CREATE TABLE user_sign_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sign_id VARCHAR(50) NOT NULL,
                course VARCHAR(50) NOT NULL,
                total_attempts INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_practiced_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES user(id),
                UNIQUE (user_id, sign_id, course)
            )
        """)
        conn.commit()
        print("[SUCCESS] Table created successfully!")

except Exception as e:
    print(f"\n[ERROR] {e}")
    conn.rollback()
    raise
finally:
    conn.close()
    print("\n[*] Database connection closed")
