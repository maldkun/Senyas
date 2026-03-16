"""
Add unlock columns to User table for Dynamic Difficulty
"""

import sqlite3
import os

db_path = os.path.join('instance', 'database.db')

def add_user_columns():
    """Add Dynamic unlock columns to User table"""
    
    if not os.path.exists(db_path):
        print(f"!! Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print(">> Adding unlock columns to User table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(user)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        columns_to_add = [
            ('dynamic_alphabets_unlocked', 'INTEGER DEFAULT 0'),
            ('dynamic_words_unlocked', 'INTEGER DEFAULT 0'),
            ('dynamic_phrases_unlocked', 'INTEGER DEFAULT 0')
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                sql = f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"
                print(f"  Adding column: {col_name}")
                cursor.execute(sql)
            else:
                print(f"  Column already exists: {col_name}")
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(user)")
        final_columns = [row[1] for row in cursor.fetchall()]
        
        print("\n>> User table columns after migration:")
        for col in final_columns:
            print(f"  - {col}")
        
        print("\n>> Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n!! Error: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    success = add_user_columns()
    sys.exit(0 if success else 1)
