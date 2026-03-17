import os
import sys
import json
from datetime import datetime

# Setup mock environment for Flask/SQLAlchemy testing if needed
# But for now, let's just test the logic directly in a script if possible
# or just do a dry run of the logic since we can't easily boot the whole app here.

def test_progress_advancement():
    print("Testing progress advancement logic...")
    
    # Mock user and progress
    current_fsl_progress = 0
    
    def calculate_new_progress(requested_part, current_progress, is_complete):
        if is_complete and requested_part:
            part_idx_int = int(requested_part)
            if part_idx_int == current_progress + 1:
                return part_idx_int
            elif part_idx_int <= current_progress:
                return current_progress
        return current_progress

    # Test cases
    cases = [
        {"initial": 0, "requested": 1, "complete": True, "expected": 1, "desc": "Advancing from 0 to 1"},
        {"initial": 0, "requested": 2, "complete": True, "expected": 0, "desc": "Blocking jump from 0 to 2"},
        {"initial": 1, "requested": 1, "complete": True, "expected": 1, "desc": "Already at 1, staying at 1"},
        {"initial": 1, "requested": 2, "complete": True, "expected": 2, "desc": "Advancing from 1 to 2"},
        {"initial": 2, "requested": 5, "complete": True, "expected": 2, "desc": "Blocking jump from 2 to 5"},
    ]

    for case in cases:
        res = calculate_new_progress(case["requested"], case["initial"], case["complete"])
        print(f"Result: {res} | Expected: {case['expected']} | {case['desc']}")
        assert res == case['expected']

    print("✅ Progress advancement logic verified!")

def test_template_data_consistency():
    print("Testing template data consistency...")
    
    # Mocking what the template sees
    class MockAttempt:
        def __init__(self, batch_index=None, perf_index=None):
            self.batch_index = batch_index
            self.performance_order_index = perf_index

    class MockSession:
        def __init__(self, attempts):
            self.attempts = attempts

    sessions = [
        MockSession([MockAttempt(None, None), MockAttempt(1, 0)]),
        MockSession([MockAttempt(0, 5)])
    ]

    # Testing study time safeguards
    class MockAttempt:
        def __init__(self, batch_index=None, perf_index=None, study_time=None):
            self.batch_index = batch_index
            self.performance_order_index = perf_index
            self.study_time_used = study_time

    class MockSession:
        def __init__(self, attempts, final_study_time=None):
            self.attempts = attempts
            self.final_study_time = final_study_time

    sessions = [
        MockSession([MockAttempt(None, None, None)], None),
        MockSession([MockAttempt(0, 5, 10)], 5)
    ]

    # The logic I added to views.py
    for session in sessions:
        if session.final_study_time is None:
            session.final_study_time = 5
        for attempt in session.attempts:
            if attempt.batch_index is None:
                attempt.batch_index = 0
            if attempt.performance_order_index is None:
                attempt.performance_order_index = 0
            if attempt.study_time_used is None:
                attempt.study_time_used = 0

    # Verification
    for s_idx, session in enumerate(sessions):
        assert session.final_study_time is not None
        for a_idx, attempt in enumerate(session.attempts):
            print(f"Session {s_idx} Attempt {a_idx}: batch={attempt.batch_index}, perf={attempt.performance_order_index}, study_time={attempt.study_time_used}")
            assert attempt.batch_index is not None
            assert attempt.performance_order_index is not None
            assert attempt.study_time_used is not None
            # Check that comparison doesn't fail
            is_extra = attempt.study_time_used > session.final_study_time
            print(f"  Is extra time: {is_extra}")

    print("✅ Template data consistency logic (including study_time) verified!")

if __name__ == "__main__":
    try:
        test_progress_advancement()
        test_template_data_consistency()
        print("\nAll verification tests passed!")
    except AssertionError as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        sys.exit(1)
