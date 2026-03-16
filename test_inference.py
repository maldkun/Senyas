import sys
import os
import json
import traceback
import numpy as np

# Mock the current user requirement temporarily if needed, or just import the module directly
try:
    print("Test 1: Importing fsl_inference...")
    sys.path.insert(0, os.path.abspath('Sign Language model'))
    from fsl_inference import FSLInferenceEngine
    
    print("Test 2: Instantiating Engine...")
    engine = FSLInferenceEngine()
    
    if engine.model is None:
        print("FAILED: Model did not load. Checking paths...")
        print(f"Looked in: {engine.model_dir}")
        print(f"fsl_model.h5 exists: {os.path.exists(os.path.join(engine.model_dir, 'fsl_model.h5'))}")
    else:
        print("SUCCESS: Model loaded.")
        
        print("Test 3: Running dummy prediction...")
        dummy_landmarks = np.random.rand(63).astype(np.float32)
        result = engine.get_smoothed_prediction(dummy_landmarks, "test_session")
        print(f"Prediction result: {result}")
        
except Exception as e:
    print("\n--- CRASH DUMP ---")
    print(traceback.format_exc())
