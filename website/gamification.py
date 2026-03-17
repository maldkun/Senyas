"""
gamification.py
Core gamification logic: EXP awarding, level calculation, streak tracking,
and achievement detection for the FSL e-learning platform.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import func as sqla_func
from . import db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXP_PER_LEVEL = 150
MAX_LEVEL = 10
MAX_STREAK_BONUS = 50

LEVEL_TITLES = {
    1: "Beginner Signer",
    2: "Learning Hands",
    3: "Signing Student",
    4: "Confident Signer",
    5: "Skilled Hands",
    6: "Advanced Signer",
    7: "Expert Hands",
    8: "Master Signer",
    9: "FSL Champion",
    10: "Sign Language Legend",
}

LEVEL_UNLOCKS = {
    2: ["Words Course Access"],
    3: ["Statistics Dashboard"],
    4: ["Phrases Course Access"],
    5: ["Custom Avatar Upload"],
    6: ["Theme Customization"],
    7: ["Achievement Showcase"],
    8: ["Leaderboard Access"],
    9: ["Expert Challenges Mode"],
    10: ["Mentor Badge", "Certificate of Completion"],
}

# ---------------------------------------------------------------------------
# Level Helpers
# ---------------------------------------------------------------------------

def calculate_level(total_exp: int) -> int:
    """Return level (1–10) for the given total EXP."""
    level = (total_exp // EXP_PER_LEVEL) + 1
    return min(level, MAX_LEVEL)


def get_level_title(level: int) -> str:
    return LEVEL_TITLES.get(level, "FSL Learner")


def get_exp_to_next_level(total_exp: int) -> int:
    level = calculate_level(total_exp)
    if level >= MAX_LEVEL:
        return 0
    next_level_exp = level * EXP_PER_LEVEL
    return next_level_exp - total_exp


def get_level_progress_percent(total_exp: int) -> float:
    level = calculate_level(total_exp)
    if level >= MAX_LEVEL:
        return 100.0
    current_level_exp = total_exp % EXP_PER_LEVEL
    return round((current_level_exp / EXP_PER_LEVEL) * 100, 1)


def get_level_unlocks(level: int) -> list:
    return LEVEL_UNLOCKS.get(level, [])

# ---------------------------------------------------------------------------
# Streak helpers
# ---------------------------------------------------------------------------

def calculate_streak_bonus(streak_days: int) -> int:
    """Return EXP bonus for streak: +10/day, max 50."""
    return min(streak_days * 10, MAX_STREAK_BONUS)

# ---------------------------------------------------------------------------
# User Progress
# ---------------------------------------------------------------------------

def get_or_create_user_progress(user_id: int):
    """Get existing UserProgress or create a fresh one."""
    from .models import UserProgress
    prog = UserProgress.query.filter_by(user_id=user_id).first()
    if prog is None:
        prog = UserProgress(user_id=user_id)
        db.session.add(prog)
        db.session.commit()
    return prog


def ensure_all_stats_exist(user_id: int, course: str = 'alphabets'):
    """
    Ensure UserSignStats has an entry for every sign in the course.
    Useful for research exports so the CSV doesn't have missing rows.
    """
    from .models import UserSignStats
    
    if course == 'alphabets':
        all_signs = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    else:
        # For words or phrases, we could add them as they are defined
        return 

    existing_signs = {s.sign_id for s in UserSignStats.query.filter_by(
        user_id=user_id, course=course).all()}
    
    added = False
    for sign in all_signs:
        if sign not in existing_signs:
            stats = UserSignStats(
                user_id=user_id,
                sign_id=sign,
                course=course,
                total_attempts=0,
                correct_count=0,
                avg_confidence=0.0,
                last_5_attempts="[]"
            )
            db.session.add(stats)
            added = True
            
    if added:
        db.session.commit()

# ---------------------------------------------------------------------------
# Core EXP awarding
# ---------------------------------------------------------------------------

def award_exp(user_id: int, exp_amount: int, source: str,
              session_id=None, attempt_id=None) -> dict:
    """
    Award EXP to a user.  Returns a dict describing old/new state.
    """
    from .models import UserProgress, EXPTransaction

    prog = get_or_create_user_progress(user_id)
    old_exp   = prog.total_exp
    old_level = prog.current_level

    new_exp   = old_exp + exp_amount
    new_level = calculate_level(new_exp)
    levels_gained = new_level - old_level

    prog.total_exp     = new_exp
    prog.current_level = new_level

    # Log transaction
    tx = EXPTransaction(
        user_id=user_id,
        session_id=session_id,
        sign_attempt_id=attempt_id,
        exp_amount=exp_amount,
        exp_source=source,
        description=f"Earned {exp_amount} EXP from {source}",
    )
    db.session.add(tx)
    db.session.commit()

    # Build level-up reward info
    level_up_rewards = []
    if levels_gained > 0:
        for lvl in range(old_level + 1, new_level + 1):
            level_up_rewards.append({
                "level":   lvl,
                "title":   get_level_title(lvl),
                "unlocks": get_level_unlocks(lvl),
            })

    return {
        "exp_awarded":      exp_amount,
        "old_exp":          old_exp,
        "new_exp":          new_exp,
        "old_level":        old_level,
        "new_level":        new_level,
        "levels_gained":    levels_gained,
        "exp_to_next_level": get_exp_to_next_level(new_exp),
        "level_progress":   get_level_progress_percent(new_exp),
        "level_up_rewards": level_up_rewards,
        "is_max_level":     new_level >= MAX_LEVEL,
        "level_title":      get_level_title(new_level),
    }

# ---------------------------------------------------------------------------
# Sign-level EXP
# ---------------------------------------------------------------------------

def calculate_sign_exp(user_id: int, session_id: int, attempt_id: int,
                       was_correct: bool, ai_confidence: float) -> dict:
    """Award EXP for a single sign attempt."""
    exp = 0
    bonuses = []

    if was_correct:
        exp += 10
        if ai_confidence and ai_confidence * 100 >= 90:
            exp += 5
            bonuses.append({"type": "perfect_sign", "amount": 5,
                            "description": "Perfect Sign! (≥90% confidence)"})
    else:
        exp += 2  # participation

    result = award_exp(user_id, exp,
                       "sign_correct" if was_correct else "sign_incorrect",
                       session_id=session_id, attempt_id=attempt_id)

    # Persist on the attempt record
    from .models import SignAttempt
    attempt = SignAttempt.query.get(attempt_id)
    if attempt:
        attempt.exp_earned = exp
        db.session.commit()

    return {"exp": exp, "bonuses": bonuses, "level_data": result}

# ---------------------------------------------------------------------------
# Batch-level EXP
# ---------------------------------------------------------------------------

def calculate_batch_exp(user_id: int, session_id: int,
                        correct_in_batch: int, total_in_batch: int) -> dict:
    """Award EXP for completing one batch of signs."""
    exp = 15  # base
    bonuses = []

    if correct_in_batch == 3 and total_in_batch == 3:
        exp += 10
        bonuses.append({"type": "perfect_batch", "amount": 10,
                        "description": "Perfect Batch! (3/3 correct)"})
    elif correct_in_batch == 2 and total_in_batch == 3:
        exp += 5
        bonuses.append({"type": "good_batch", "amount": 5,
                        "description": "Good Batch (2/3 correct)"})

    result = award_exp(user_id, exp, "batch_complete", session_id=session_id)
    return {"exp": exp, "bonuses": bonuses, "level_data": result}

# ---------------------------------------------------------------------------
# Session-level EXP
# ---------------------------------------------------------------------------

def is_first_session_today(user_id: int, session_id: int) -> bool:
    """True if this session is the user's first completed session today."""
    from .models import DynamicSession
    today = date.today()
    count = DynamicSession.query.filter(
        DynamicSession.user_id == user_id,
        DynamicSession.completed_at.isnot(None),
        sqla_func.date(DynamicSession.completed_at) == today,
    ).count()
    # count includes the session being completed now
    return count <= 1


def calculate_session_exp(user_id: int, session_id: int,
                           correct_count: int, total_signs: int,
                           completed_at_hour: int = None) -> dict:
    """Award EXP for completing a full session."""
    exp = 50  # base completion
    bonuses = []

    success_rate = (correct_count / total_signs * 100) if total_signs else 0

    if success_rate == 100:
        exp += 50
        bonuses.append({"type": "flawless_session", "amount": 50,
                        "description": "Flawless Session! (15/15 correct)"})
    elif success_rate >= 80:
        exp += 25
        bonuses.append({"type": "excellent_session", "amount": 25,
                        "description": "Excellent Session! (≥80% correct)"})

    # Daily first session bonus
    if is_first_session_today(user_id, session_id):
        exp += 20
        bonuses.append({"type": "daily_first", "amount": 20,
                        "description": "First session of the day!"})

    # Streak bonus
    prog = get_or_create_user_progress(user_id)
    streak_bonus = calculate_streak_bonus(prog.current_streak_days)
    if streak_bonus > 0:
        exp += streak_bonus
        bonuses.append({"type": "streak_bonus", "amount": streak_bonus,
                        "description": f"{prog.current_streak_days}-day streak!"})

    result = award_exp(user_id, exp, "session_complete", session_id=session_id)

    # Update session record
    from .models import DynamicSession
    sess = DynamicSession.query.get(session_id)
    if sess:
        sess.exp_earned       = exp
        sess.level_before     = result["old_level"]
        sess.level_after      = result["new_level"]
        sess.level_ups_occurred = result["levels_gained"]
        db.session.commit()

    # Update counters on UserProgress
    prog = get_or_create_user_progress(user_id)
    prog.total_sessions_completed += 1
    prog.total_signs_attempted    += total_signs
    prog.total_signs_correct      += correct_count
    db.session.commit()

    return {"exp": exp, "bonuses": bonuses, "level_data": result}

# ---------------------------------------------------------------------------
# Streak tracking
# ---------------------------------------------------------------------------

def update_streak(user_id: int) -> dict:
    """Update daily streak for user.  Call once per session completion."""
    prog  = get_or_create_user_progress(user_id)
    today = date.today()
    last  = prog.last_practice_date

    new_streak = prog.current_streak_days

    if last is None:
        new_streak = 1
    else:
        delta = (today - last).days
        if delta == 0:
            # Already practiced today
            return {
                "streak_days":  new_streak,
                "streak_bonus": calculate_streak_bonus(new_streak),
                "is_new_day":   False,
            }
        elif delta == 1:
            new_streak += 1
        else:
            new_streak = 1

    prog.current_streak_days = new_streak
    prog.longest_streak_days = max(new_streak, prog.longest_streak_days)
    prog.last_practice_date  = today
    db.session.commit()

    # Check streak achievements (after commit so counters are correct)
    check_streak_achievements(user_id, new_streak)

    return {
        "streak_days":  new_streak,
        "longest_streak": prog.longest_streak_days,
        "streak_bonus": calculate_streak_bonus(new_streak),
        "is_new_day":   True,
    }

# ---------------------------------------------------------------------------
# Achievement helpers
# ---------------------------------------------------------------------------

def check_and_unlock_achievement(user_id: int, achievement_key: str):
    """Unlock achievement if not already unlocked.  Returns unlock dict or None."""
    from .models import Achievement, UserAchievement

    ach = Achievement.query.filter_by(achievement_key=achievement_key).first()
    if ach is None:
        return None

    existing = UserAchievement.query.filter_by(
        user_id=user_id, achievement_id=ach.id
    ).first()
    if existing:
        return None  # already unlocked

    ua = UserAchievement(user_id=user_id, achievement_id=ach.id)
    db.session.add(ua)
    db.session.commit()

    # Award EXP reward
    award_exp(user_id, ach.exp_reward, "achievement_unlock")

    return {
        "achievement": {
            "key":         ach.achievement_key,
            "name":        ach.name,
            "description": ach.description,
            "badge_icon":  ach.badge_icon,
            "category":    ach.category,
        },
        "exp_rewarded": ach.exp_reward,
    }

# ---------------------------------------------------------------------------
# Achievement detection
# ---------------------------------------------------------------------------

def check_sign_achievements(user_id: int, was_correct: bool,
                             ai_confidence: float) -> list:
    unlocked = []

    if was_correct:
        prog = get_or_create_user_progress(user_id)
        if prog.total_signs_correct == 1:
            r = check_and_unlock_achievement(user_id, "first_steps")
            if r:
                unlocked.append(r)

        if ai_confidence and ai_confidence * 100 >= 90:
            r = check_and_unlock_achievement(user_id, "perfect_sign")
            if r:
                unlocked.append(r)

    return unlocked


def check_batch_achievements(user_id: int,
                              correct_in_batch: int, total_in_batch: int) -> list:
    unlocked = []
    if correct_in_batch == 3 and total_in_batch == 3:
        r = check_and_unlock_achievement(user_id, "perfect_batch")
        if r:
            unlocked.append(r)
    return unlocked


def check_session_achievements(user_id: int, session_id: int,
                                correct_count: int, total_signs: int,
                                mode: str = "static",
                                first_batch_correct: int = None) -> list:
    from .models import DynamicSession, UserProgress
    unlocked = []

    success_rate = (correct_count / total_signs * 100) if total_signs else 0

    # Flawless session
    if success_rate == 100:
        r = check_and_unlock_achievement(user_id, "flawless_session")
        if r:
            unlocked.append(r)

    # Comeback Kid (hidden): ≥80% after 0/3 first batch
    if first_batch_correct == 0 and success_rate >= 80:
        r = check_and_unlock_achievement(user_id, "comeback_kid")
        if r:
            unlocked.append(r)

    # Quick Learner: 5 sessions ≥80%
    good_sessions = DynamicSession.query.filter(
        DynamicSession.user_id == user_id,
        DynamicSession.completed_at.isnot(None),
        DynamicSession.total_signs > 0,
        (DynamicSession.correct_count * 100.0 / DynamicSession.total_signs) >= 80
    ).count()
    if good_sessions >= 5:
        r = check_and_unlock_achievement(user_id, "quick_learner")
        if r:
            unlocked.append(r)

    # Engagement: 10 / 25 sessions
    prog = get_or_create_user_progress(user_id)
    if prog.total_sessions_completed == 10:
        r = check_and_unlock_achievement(user_id, "dedicated_learner")
        if r:
            unlocked.append(r)
    if prog.total_sessions_completed == 25:
        r = check_and_unlock_achievement(user_id, "committed_student")
        if r:
            unlocked.append(r)

    # Early bird: session started before 9 AM
    sess = DynamicSession.query.get(session_id)
    if sess and sess.started_at:
        hour = sess.started_at.hour
        if 6 <= hour < 9:
            r = check_and_unlock_achievement(user_id, "early_bird")
            if r:
                unlocked.append(r)

    # Mode Explorer: tried all 3 modes
    from .models import DynamicSession as DS
    modes_used = db.session.query(sqla_func.distinct(DS.mode)).filter(
        DS.user_id == user_id,
        DS.completed_at.isnot(None),
        DS.mode.in_(["static", "dynamic", "ai"]),
    ).all()
    modes_set = {m[0] for m in modes_used}
    if {"static", "dynamic", "ai"}.issubset(modes_set):
        r = check_and_unlock_achievement(user_id, "mode_explorer")
        if r:
            unlocked.append(r)

    # AI Apprentice: 5 AI sessions
    ai_count = DynamicSession.query.filter(
        DynamicSession.user_id == user_id,
        DynamicSession.mode == "ai",
        DynamicSession.completed_at.isnot(None),
    ).count()
    if ai_count >= 5:
        r = check_and_unlock_achievement(user_id, "ai_apprentice")
        if r:
            unlocked.append(r)

    # Alphabet Master: all 26 signs ≥85% avg in alphabets
    from .models import UserSignStats
    alphabet_stats = UserSignStats.query.filter(
        UserSignStats.user_id == user_id,
        UserSignStats.course == "alphabets",
    ).all()
    if len(alphabet_stats) >= 26:
        all_mastered = all(
            (s.correct_count / s.total_attempts * 100) >= 85
            for s in alphabet_stats if s.total_attempts > 0
        )
        if all_mastered:
            r = check_and_unlock_achievement(user_id, "alphabet_master")
            if r:
                unlocked.append(r)

    return unlocked


def check_streak_achievements(user_id: int, streak_days: int) -> list:
    unlocked = []
    milestones = [
        (3, "getting_started"),
        (7, "building_habits"),
        (14, "unstoppable"),
    ]
    for days, key in milestones:
        if streak_days >= days:
            r = check_and_unlock_achievement(user_id, key)
            if r:
                unlocked.append(r)
    return unlocked

# ---------------------------------------------------------------------------
# Achievement seeding
# ---------------------------------------------------------------------------

ACHIEVEMENTS_DATA = [
    # Performance
    {"key": "first_steps",      "name": "First Steps",       "desc": "Complete your first sign correctly",        "cat": "performance", "badge": "🏅",       "exp": 30,  "hidden": False, "order": 1},
    {"key": "perfect_sign",     "name": "Perfect Sign",      "desc": "Perform a sign with ≥90% AI confidence",   "cat": "performance", "badge": "⭐",       "exp": 20,  "hidden": False, "order": 2},
    {"key": "perfect_batch",    "name": "Perfect Batch",     "desc": "Complete a batch with 3/3 correct",         "cat": "performance", "badge": "🎯",       "exp": 30,  "hidden": False, "order": 3},
    {"key": "flawless_session", "name": "Flawless Session",  "desc": "Complete a session with 15/15 correct",     "cat": "performance", "badge": "💎",       "exp": 100, "hidden": False, "order": 4},
    {"key": "quick_learner",    "name": "Quick Learner",     "desc": "Complete 5 sessions with ≥80% accuracy",    "cat": "performance", "badge": "🚀",       "exp": 50,  "hidden": False, "order": 5},
    {"key": "alphabet_master",  "name": "Alphabet Master",   "desc": "Master all 26 signs with ≥85% accuracy",   "cat": "performance", "badge": "📚",       "exp": 150, "hidden": False, "order": 6},
    # Engagement
    {"key": "dedicated_learner","name": "Dedicated Learner", "desc": "Complete 10 sessions",                      "cat": "engagement",  "badge": "📖",       "exp": 80,  "hidden": False, "order": 7},
    {"key": "committed_student","name": "Committed Student", "desc": "Complete 25 sessions",                      "cat": "engagement",  "badge": "🎓",       "exp": 150, "hidden": False, "order": 8},
    {"key": "early_bird",       "name": "Early Bird",        "desc": "Practice before 9 AM",                      "cat": "engagement",  "badge": "🌅",       "exp": 25,  "hidden": False, "order": 9},
    # Streak
    {"key": "getting_started",  "name": "Getting Started",   "desc": "Achieve a 3-day practice streak",           "cat": "streak",      "badge": "🔥",       "exp": 40,  "hidden": False, "order": 10},
    {"key": "building_habits",  "name": "Building Habits",   "desc": "Achieve a 7-day practice streak",           "cat": "streak",      "badge": "🔥🔥",     "exp": 80,  "hidden": False, "order": 11},
    {"key": "unstoppable",      "name": "Unstoppable",       "desc": "Achieve a 14-day practice streak",          "cat": "streak",      "badge": "🔥🔥🔥",   "exp": 150, "hidden": False, "order": 12},
    # Mode
    {"key": "mode_explorer",    "name": "Mode Explorer",     "desc": "Try all 3 difficulty modes",                "cat": "mode",        "badge": "🧭",       "exp": 50,  "hidden": False, "order": 13},
    {"key": "ai_apprentice",    "name": "AI Apprentice",     "desc": "Complete 5 AI Difficulty sessions",         "cat": "mode",        "badge": "🤖",       "exp": 80,  "hidden": False, "order": 14},
    # Hidden
    {"key": "comeback_kid",     "name": "Comeback Kid",      "desc": "Score ≥80% after 0/3 on the first batch",  "cat": "hidden",      "badge": "💪",       "exp": 80,  "hidden": True,  "order": 15},
]


def seed_achievements():
    """Insert all achievements into the DB (idempotent)."""
    from .models import Achievement
    count = 0
    for a in ACHIEVEMENTS_DATA:
        existing = Achievement.query.filter_by(achievement_key=a["key"]).first()
        if existing is None:
            ach = Achievement(
                achievement_key=a["key"],
                name=a["name"],
                description=a["desc"],
                category=a["cat"],
                badge_icon=a["badge"],
                exp_reward=a["exp"],
                is_hidden=a["hidden"],
                sort_order=a["order"],
            )
            db.session.add(ach)
            count += 1
    db.session.commit()
    print("Seeded {} new achievements ({} total defined)".format(count, len(ACHIEVEMENTS_DATA)))
    return count
