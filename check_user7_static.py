import sqlite3
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# Check static sessions for user 7
cursor.execute(
    'SELECT COUNT(*) FROM dynamic_session WHERE user_id = 7 AND mode = "static"')
user7_static = cursor.fetchone()[0]
print(f'Static sessions for user 7: {user7_static}')

# Check all users with static sessions
cursor.execute(
    'SELECT user_id, COUNT(*) FROM dynamic_session WHERE mode = "static" GROUP BY user_id')
users_static = cursor.fetchall()
print('Users with static sessions:')
for user_id, count in users_static:
    print(f'  User {user_id}: {count} static sessions')

conn.close()
