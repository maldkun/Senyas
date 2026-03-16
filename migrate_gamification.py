"""
migrate_gamification.py
Run this script ONCE to:
  1. Create the new gamification tables
  2. Add new columns to existing tables
  3. Seed 15 achievements
  4. Initialize UserProgress for all existing users
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from website import create_app, db

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Gamification Migration")
    print("=" * 60)

    # 1. Create all tables
    print("\n[1/4] Creating new gamification tables...")
    db.create_all()
    print("      OK: Tables created / verified")

    # 2. Add columns to existing tables
    print("\n[2/4] Adding gamification columns to existing tables...")

    from sqlalchemy import text, inspect
    inspector = inspect(db.engine)

    def add_column_if_missing(table, column_def, column_name):
        cols = [c["name"] for c in inspector.get_columns(table)]
        if column_name not in cols:
            db.session.execute(text(
                "ALTER TABLE {} ADD COLUMN {}".format(table, column_def)
            ))
            print("      + {}.{}".format(table, column_name))
        else:
            print("      ~ {}.{} (already exists)".format(table, column_name))

    add_column_if_missing("dynamic_session", "mode VARCHAR(20) DEFAULT 'static'", "mode")
    add_column_if_missing("dynamic_session", "exp_earned INTEGER DEFAULT 0", "exp_earned")
    add_column_if_missing("dynamic_session", "level_before INTEGER DEFAULT 1", "level_before")
    add_column_if_missing("dynamic_session", "level_after INTEGER DEFAULT 1", "level_after")
    add_column_if_missing("dynamic_session", "level_ups_occurred INTEGER DEFAULT 0", "level_ups_occurred")
    add_column_if_missing("sign_attempt", "exp_earned INTEGER DEFAULT 0", "exp_earned")

    db.session.commit()
    print("      OK: Columns updated")

    # 3. Seed achievements
    print("\n[3/4] Seeding achievements...")
    from website.gamification import seed_achievements
    seed_achievements()

    # 4. Initialize UserProgress
    print("\n[4/4] Initializing UserProgress for existing users...")
    from website.models import User, UserProgress
    users = User.query.all()
    created = 0
    for user in users:
        exists = UserProgress.query.filter_by(user_id=user.id).first()
        if not exists:
            prog = UserProgress(user_id=user.id)
            db.session.add(prog)
            created += 1
    db.session.commit()
    print("      OK: {} new UserProgress records ({} total users)".format(created, len(users)))

    print("\n" + "=" * 60)
    print("Gamification system initialized successfully!")
    print("  Level cap    : 10")
    print("  EXP per level: 150")
    print("  Achievements : 15")
    print("=" * 60)
