import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from website import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Applying AI Mode Database Migrations")
    print("=" * 60)

    # 1. Create any missing tables (like ai_sign_stats)
    print("\n[1/2] Creating missing tables...")
    db.create_all()
    print("      OK: Tables created / verified")

    # 2. Add columns to existing tables
    print("\n[2/2] Adding new columns to existing tables...")

    inspector = inspect(db.engine)

    def add_column_if_missing(table, column_def, column_name):
        try:
            # Note: For psycopg2, we need to ensure table name is not quoted incorrectly in some setups, but this standard way works.
            cols = [c["name"] for c in inspector.get_columns(table)]
            if column_name not in cols:
                db.session.execute(text(
                    "ALTER TABLE {} ADD COLUMN {}".format(table, column_def)
                ))
                print("      + {}.{}".format(table, column_name))
            else:
                print("      ~ {}.{} (already exists)".format(table, column_name))
        except Exception as e:
            print("      ! Error checking/adding {}.{}: {}".format(table, column_name, e))

    add_column_if_missing("user_sign_stats", "practice_mode VARCHAR(20) DEFAULT 'static'", "practice_mode")

    db.session.commit()
    print("      OK: Columns updated")

    print("\n" + "=" * 60)
    print("AI Mode migration completed successfully!")
    print("=" * 60)
