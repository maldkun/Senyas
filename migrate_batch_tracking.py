import sqlite3
import os

DB_PATH = os.path.join('instance', 'database.db')

def add_columns():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("batch_index", "INTEGER"),
        ("batch_size", "INTEGER"),
        ("study_order_index", "INTEGER"),
        ("performance_order_index", "INTEGER")
    ]

    for col_name, col_type in columns_to_add:
        try:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE sign_attempt ADD COLUMN {col_name} {col_type}")
            print(f"Successfully added {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"Column {col_name} already exists. Skipping.")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    add_columns()
