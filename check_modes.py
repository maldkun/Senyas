import sqlite3
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# Check all modes in the database
cursor.execute('SELECT mode, COUNT(*) FROM dynamic_session GROUP BY mode')
modes = cursor.fetchall()
print('All session modes in database:')
for mode, count in modes:
    print(f'  {mode}: {count} sessions')

# Check if static mode exists anywhere
cursor.execute(
    'SELECT COUNT(*) FROM dynamic_session WHERE mode LIKE "%static%"')
static_like = cursor.fetchone()[0]
print(f'Sessions with "static" in mode: {static_like}')

conn.close()
