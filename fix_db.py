import sqlite3

conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

try:
    cursor.execute(
        'ALTER TABLE user_sign_stats ADD COLUMN avg_confidence FLOAT DEFAULT 0.0')
    cursor.execute(
        'ALTER TABLE user_sign_stats ADD COLUMN last_5_attempts TEXT DEFAULT "[]"')
    conn.commit()
    print('Columns added successfully')
except Exception as e:
    print(f'Error: {e}')
    conn.rollback()
finally:
    conn.close()
