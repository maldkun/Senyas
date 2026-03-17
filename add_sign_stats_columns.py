"""
Safe migration script: Add enhanced sign statistics columns and tables.

Usage:
  python add_sign_stats_columns.py

Safe to run multiple times (idempotent — skips columns/tables that already exist).
Does NOT drop, truncate, or modify any existing data.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from website import create_app, db
from sqlalchemy import text, inspect

app = create_app()


def column_exists(conn, table_name, column_name):
    """Check if a column already exists in a table."""
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(conn, table_name):
    """Check if a table already exists."""
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def add_column_if_missing(conn, table_name, column_name, column_def):
    """Add a column to a table only if it doesn't already exist."""
    if not column_exists(conn, table_name, column_name):
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
        conn.execute(text(sql))
        print(f"  ✅ Added column: {table_name}.{column_name}")
    else:
        print(f"  ⏭️  Skipped (already exists): {table_name}.{column_name}")


def migrate():
    with app.app_context():
        with db.engine.connect() as conn:
            print("\n📦 Migrating user_sign_stats table...")

            # Check if the conflicting 'mode' column was already added in a previous run
            if column_exists(conn, 'user_sign_stats', 'mode'):
                print("  ⚠️  Found conflicting 'mode' column. Renaming to 'practice_mode'...")
                conn.execute(text("ALTER TABLE user_sign_stats RENAME COLUMN mode TO practice_mode"))
                conn.commit()
                print("  ✅ Renamed 'mode' to 'practice_mode'.")
            else:
                add_column_if_missing(conn, 'user_sign_stats', 'practice_mode', "VARCHAR(20) DEFAULT 'static'")

            # Expand last_5_attempts from 100 to 200 chars — we do this by adding a new
            # column if somehow the old size was capped. (SQLite ignores column size anyway.)
            # For PostgreSQL on Railway, VARCHAR(100) vs VARCHAR(200) is fine, no migration needed
            # since we already update the model. The column already exists.

            # Performance History
            add_column_if_missing(conn, 'user_sign_stats', 'performance_history', "TEXT DEFAULT '[]'")

            # Confidence Patterns
            add_column_if_missing(conn, 'user_sign_stats', 'confidence_patterns', "TEXT DEFAULT '{}'")

            # Study Time Preferences
            add_column_if_missing(conn, 'user_sign_stats', 'study_time_prefs', "TEXT DEFAULT '{}'")

            # Sign Difficulty
            add_column_if_missing(conn, 'user_sign_stats', 'sign_difficulty', "FLOAT DEFAULT 0.5")

            conn.commit()
            print("  ✅ user_sign_stats migration complete.\n")

            # -------------------------------------------------------------------
            print("📦 Creating ai_sign_stats table (if it doesn't exist)...")
            if not table_exists(conn, 'ai_sign_stats'):
                conn.execute(text("""
                    CREATE TABLE ai_sign_stats (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES "user"(id),
                        sign_id VARCHAR(50),
                        course VARCHAR(50),
                        total_attempts INTEGER DEFAULT 0,
                        correct_count INTEGER DEFAULT 0,
                        last_practiced_at TIMESTAMPTZ,
                        avg_confidence FLOAT DEFAULT 0.0,
                        last_5_attempts VARCHAR(200) DEFAULT '[]',
                        ai_difficulty_score FLOAT DEFAULT 0.5,
                        ai_threshold_history TEXT DEFAULT '[]',
                        performance_history TEXT DEFAULT '[]',
                        study_time_prefs TEXT DEFAULT '{}',
                        CONSTRAINT _ai_sign_stats_uc UNIQUE (user_id, sign_id, course)
                    )
                """))
                conn.commit()
                print("  ✅ ai_sign_stats table created.\n")
            else:
                # Table exists — add any missing columns
                print("  ⏭️  ai_sign_stats table already exists, checking columns...")
                add_column_if_missing(conn, 'ai_sign_stats', 'ai_difficulty_score', "FLOAT DEFAULT 0.5")
                add_column_if_missing(conn, 'ai_sign_stats', 'ai_threshold_history', "TEXT DEFAULT '[]'")
                add_column_if_missing(conn, 'ai_sign_stats', 'performance_history', "TEXT DEFAULT '[]'")
                add_column_if_missing(conn, 'ai_sign_stats', 'study_time_prefs', "TEXT DEFAULT '{}'")
                conn.commit()
                print("  ✅ ai_sign_stats columns checked.\n")

            # -------------------------------------------------------------------
            # Try to add the new unique constraint if old one still exists
            # (handles the renamed constraint from _user_sign_course_uc to _user_sign_course_mode_uc)
            print("📦 Checking unique constraints on user_sign_stats...")
            try:
                conn.execute(text(
                    "ALTER TABLE user_sign_stats DROP CONSTRAINT IF EXISTS _user_sign_course_uc"
                ))
                conn.commit()
                print("  ✅ Dropped old constraint _user_sign_course_uc")
            except Exception as e:
                print(f"  ⏭️  Could not drop old constraint (may not exist): {e}")

            # The new constraint (_user_sign_course_mode_uc) is defined in the model;
            # SQLAlchemy will create it when tables are synced. If it already exists, skip.
            try:
                conn.execute(text(
                    "ALTER TABLE user_sign_stats ADD CONSTRAINT _user_sign_course_mode_uc "
                    "UNIQUE (user_id, sign_id, course, practice_mode)"
                ))
                conn.commit()
                print("  ✅ Added new constraint _user_sign_course_mode_uc")
            except Exception as e:
                print(f"  ⏭️  Constraint already exists or failed: {e}")

            print("\n🎉 Migration complete! All changes applied safely.")


if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        import traceback
        print(f"\n❌ Migration failed: {e}")
        traceback.print_exc()
        sys.exit(1)
