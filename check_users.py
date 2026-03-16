import sqlite3

conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# Unique signs
cursor.execute('SELECT user_id, COUNT(*) as unique_signs FROM user_sign_stats WHERE course="alphabets" GROUP BY user_id')
signs = cursor.fetchall()
print('Unique signs per user:', signs)

# User levels
cursor.execute('SELECT user_id, total_exp, current_level FROM user_progress')
levels = cursor.fetchall()
print('User levels:', levels)

# Check which user is logged in - let's see recent activity
cursor.execute('SELECT user_id, MAX(completed_at) as last_session FROM dynamic_session WHERE completed_at IS NOT NULL GROUP BY user_id ORDER BY last_session DESC')
recent = cursor.fetchall()
print('Recent activity:', recent)

conn.close()