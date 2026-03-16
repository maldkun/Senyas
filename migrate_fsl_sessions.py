import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from website import create_app, db
from sqlalchemy import text, inspect

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Migrating DynamicSession table for multi-worker support")
    print("=" * 60)

    inspector = inspect(db.engine)
    
    def add_column_if_missing(table, column_def, column_name):
        cols = [c["name"] for c in inspector.get_columns(table)]
        if column_name not in cols:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
            print(f"      + {table}.{column_name}")
        else:
            print(f"      ~ {table}.{column_name} (already exists)")

    add_column_if_missing("dynamic_session", "sequence_data TEXT", "sequence_data")
    add_column_if_missing("dynamic_session", "current_index INTEGER DEFAULT 0", "current_index")
    
    db.session.commit()
    print("      OK: Columns updated")
    print("=" * 60)
