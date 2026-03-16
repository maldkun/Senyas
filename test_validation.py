import sys
import os

# Create dummy model dir so FSLInferenceEngine doesn't crash on init (though we only need ProgressiveSignSequence today)
# Actually, ProgressiveSignSequence does not depend on FSLInferenceEngine class directly.
# We can just copy the ProgressiveSignSequence class or import if we set up path.

sys.path.insert(0, os.path.join(os.getcwd(), 'Sign Language model'))

from fsl_inference import ProgressiveSignSequence

def test_validation():
    print("Testing ProgressiveSignSequence...")
    
    seq = ProgressiveSignSequence()
    seq.set_sequence(list("ABC"))
    
    print(f"Target: {seq.get_current_target()}")
    
    # Test strict mismatch
    result = seq.check_sign("B", 0.9)
    print(f"Check B (expect A): Correct={result['is_correct']}, Complete={result['is_complete']}, Target={result['target']}")
    if result['is_correct']:
        print("FAIL: Should not be correct")
        
    # Test match
    result = seq.check_sign("A", 0.9)
    print(f"Check A (expect A): Correct={result['is_correct']}, Complete={result['is_complete']}, Target={result['target']}")
    
    if not result['is_correct']:
        print("FAIL: Should be correct")
    
    if result['target'] != "B":
        print(f"FAIL: Target should be B, got {result['target']}")
        
    # Test validation of B
    result = seq.check_sign("B", 0.9)
    print(f"Check B (expect B): Correct={result['is_correct']}, Complete={result['is_complete']}, Target={result['target']}")
    
    if result['target'] != "C":
        print(f"FAIL: Target should be C, got {result['target']}")
        
    # Test validation of C (Final)
    result = seq.check_sign("C", 0.9)
    print(f"Check C (expect C): Correct={result['is_correct']}, Complete={result['is_complete']}, Target={result['target']}")
    
    if not result['is_complete']:
        print("FAIL: Should be complete")

if __name__ == "__main__":
    test_validation()
