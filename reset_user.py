import sqlite3

conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

user_id = 7  # The problematic user

try:
    # Reset UserProgress
    cursor.execute('UPDATE user_progress SET total_exp = 0, current_level = 1, current_streak_days = 0, longest_streak_days = 0, last_practice_date = NULL, total_sessions_completed = 0, total_signs_attempted = 0, total_signs_correct = 0 WHERE user_id = ?', (user_id,))

    # Delete all dynamic sessions
    cursor.execute('DELETE FROM dynamic_session WHERE user_id = ?', (user_id,))

    # Delete all sign attempts
    cursor.execute('DELETE FROM sign_attempt WHERE user_id = ?', (user_id,))

    # Delete all user sign stats
    cursor.execute('DELETE FROM user_sign_stats WHERE user_id = ?', (user_id,))

    # Delete all user achievements
    cursor.execute('DELETE FROM user_achievement WHERE user_id = ?', (user_id,))

    # Reset EXP transactions
    cursor.execute('DELETE FROM exp_transaction WHERE user_id = ?', (user_id,))

    conn.commit()
    print(f"Reset all data for user {user_id}")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()