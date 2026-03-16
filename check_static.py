import sqlite3
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

print('=== STATIC MODE ANALYSIS ===')
cursor.execute(
    'SELECT COUNT(*) FROM dynamic_session WHERE user_id = 7 AND mode = "static"')
static_sessions = cursor.fetchone()[0]
print(f'Static sessions: {static_sessions}')

cursor.execute(
    'SELECT COUNT(*) FROM sign_attempt WHERE user_id = 7 AND course = "alphabets"')
static_attempts = cursor.fetchone()[0]
print(f'Static attempts: {static_attempts}')

cursor.execute(
    'SELECT DISTINCT session_id FROM sign_attempt WHERE user_id = 7 AND course = "alphabets" LIMIT 5')
session_ids = cursor.fetchall()
print(
    f'Distinct session_ids in static attempts: {[s[0] for s in session_ids]}')

# Check if static sessions exist but with different course
cursor.execute(
    'SELECT COUNT(*), course FROM dynamic_session WHERE user_id = 7 GROUP BY course')
courses = cursor.fetchall()
print(f'Session courses: {courses}')

conn.close()
