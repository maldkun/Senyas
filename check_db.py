import sqlite3

conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# Check tables
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

# Check user_sign_stats columns
cursor.execute('PRAGMA table_info(user_sign_stats)')
cols = cursor.fetchall()
print('user_sign_stats columns:', len(cols))
for col in cols:
    print(f'  {col[1]}: {col[2]}')

conn.close()
