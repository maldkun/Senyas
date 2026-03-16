"""
Database migration script for Dynamic Difficulty feature
Adds new tables and columns to existing database
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from website import create_app, db
from website.models import User, DynamicSession, SignAttempt, UserSignStats

def migrate_database():
    """Add Dynamic Difficulty tables to existing database"""
    app = create_app()
    
    with app.app_context():
        print(">> Starting database migration for Dynamic Difficulty...")
        
        try:
            # Create new tables
            print(">> Creating new tables...")
            db.create_all()
            print(">> Tables created successfully!")
            
            # Verify tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print("\n>> Current database tables:")
            for table in tables:
                print(f"  - {table}")
            
            # Check if new columns exist in User table
            user_columns = [col['name'] for col in inspector.get_columns('user')]
            print("\n>> User table columns:")
            for col in user_columns:
                print(f"  - {col}")
            
            # Verify new tables
            required_tables = ['dynamic_session', 'sign_attempt', 'user_sign_stats']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"\n!! Warning: Missing tables: {missing_tables}")
            else:
                print("\n>> All Dynamic Difficulty tables present!")
            
            # Verify new columns in User table
            required_columns = ['dynamic_alphabets_unlocked', 'dynamic_words_unlocked', 
                              'dynamic_phrases_unlocked']
            missing_columns = [c for c in required_columns if c not in user_columns]
            
            if missing_columns:
                print(f"\n!! Warning: Missing User columns: {missing_columns}")
                print("Note: If columns are missing, you may need to manually update the database.")
            else:
                print(">> All User unlock columns present!")
            
            print("\n>> Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n!! Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
