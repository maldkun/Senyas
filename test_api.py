import os
import sys
import json
from website import create_app, db
from website.models import User, DynamicSession
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    user = User.query.filter_by(email='test_api@senyas.com').first()
    if not user:
        user = User(
            email='test_api@senyas.com',
            first_name='Test',
            password=generate_password_hash('password')
        )
        db.session.add(user)
        db.session.commit()

    signs = list("ABCDE")
    
    session = DynamicSession(
        user_id=user.id,
        course='static',
        total_signs=len(signs),
        correct_count=0,
        incorrect_count=0,
        final_study_time=0,
        final_threshold=50,
        sequence_data=json.dumps(signs),
        current_index=0
    )
    db.session.add(session)
    db.session.commit()
    
    session_id = session.id
    
    # Simulate /api/fsl/sequence/progress
    sess = DynamicSession.query.get(session_id)
    seq = json.loads(sess.sequence_data)
    idx = sess.current_index
    is_comp = idx >= len(seq)
    
    progress = {
        'current_target': seq[idx] if not is_comp else None,
        'completed': seq[:idx],
        'progress_percent': int((idx / len(seq)) * 100) if seq else 100,
        'is_complete': is_comp,
        'sequence': seq
    }
    
    print("PROGRESS RESPONSE:")
    print(json.dumps(progress, indent=2))
    
    # Simulate /api/fsl/sequence/check ('A')
    target = seq[idx] if idx < len(seq) else None
    detected = 'A'
    if detected == target:
        sess.current_index += 1
        db.session.commit()
        
    idx2 = sess.current_index
    is_comp2 = idx2 >= len(seq)
    check_res = {
        'is_correct': True,
        'target': seq[idx2] if not is_comp2 else None,
        'completed': seq[:idx2],
        'progress_percent': int((idx2 / len(seq)) * 100) if seq else 100,
        'is_complete': is_comp2,
        'message': 'Correct!'
    }
    print("\nCHECK RESPONSE:")
    print(json.dumps(check_res, indent=2))

    db.session.rollback()
