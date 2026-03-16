import sys
import os
import io

# Force utf-8 for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    print(f"Check B (expect A): Correct={result['is_correct']}, Complete={result['is_complete']}, Target={result['target']}, msg={result['message']}")
    if result['is_correct']:
        print("FAIL: Should not be correct")
        
    # Test match - Frame 1 (Success - advances immediately with REQUIRED_FRAMES=1)
    print("\n--- Testing 'A' sequence (needs 1 frame) ---")
    result = seq.check_sign("A", 0.9)
    print(f"Frame 1: Correct={result['is_correct']}, Complete={result['is_complete']}, Target={result['target']}, Count={result['consecutive_count']}")
    
    if not result['is_correct']:
        print("FAIL: Should be correct")
    if result['target'] != "B": 
         print(f"FAIL: Should advance to B after 1 frame. Got {result['target']}")
        
    print("\n--- Testing 'B' with low confidence ---")
    # Test validation of B with low confidence
    result = seq.check_sign("B", 0.4)
    print(f"Check B (low conf): Correct={result['is_correct']}, Msg={result['message']}")
    
    if result.get('debug_info') != "Low confidence: 0.4":
        print("FAIL: Should warn about low confidence")

if __name__ == "__main__":
    test_validation()
