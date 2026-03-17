"""
Flask-ready FSL Inference Module
Provides functions for real-time sign prediction suitable for web integration.
"""

import os
import pickle
import threading
import numpy as np
import mediapipe as mp
import tensorflow as tf
from tensorflow import keras
from collections import defaultdict


# Global MediaPipe instance for reuse
_hands_manager = None

def get_hands_detector():
    """Lazy load MediaPipe Hands detector"""
    global _hands_manager
    if _hands_manager is None:
        try:
            import mediapipe as mp
            mp_hands = mp.solutions.hands
            _hands_manager = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.4
            )
            print("MediaPipe Hands initialized successfully")
        except Exception as e:
            print(f"FAILED TO INITIALIZE MEDIAPIPE: {e}")
            _hands_manager = False
    return _hands_manager if _hands_manager is not False else None


class FSLInferenceEngine:
    """Inference engine for FSL recognition"""
    
    
    def __init__(self, model_dir=None):
        """
        Initialize inference engine
        
        Args:
            model_dir: Path to directory containing trained models
        """
        if model_dir is None:
            # Default to 'models' subdirectory relative to this script
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.model_dir = os.path.join(base_dir, 'models')
        else:
            self.model_dir = model_dir
            
        self.model = None
        self.class_names = None
        self.scaler = None
        self.confidence_threshold = 0.0  # Force prediction
        self.lock = threading.Lock()
        
        # Prediction tracking
        self.prediction_history = defaultdict(list)
        self.max_history = 5
        
        self.load_model()
    
    def load_model(self):
        """Load trained model, classes, and scaler"""
        try:
            model_path = os.path.join(self.model_dir, 'fsl_model.h5')
            classes_path = os.path.join(self.model_dir, 'fsl_model_classes.npy')
            scaler_path = os.path.join(self.model_dir, 'landmark_scaler.pkl')
            
            
            print(f"[INFO] Model directory: {self.model_dir}")
            print(f"[INFO] Model path: {model_path}")
            print(f"[INFO] Classes path: {classes_path}")
            print(f"Loading model from: {self.model_dir}")
            print(f"Model path exists: {os.path.exists(model_path)}")
            print(f"Classes path exists: {os.path.exists(classes_path)}")
            
            if os.path.exists(model_path):
                self.model = keras.models.load_model(model_path)
                print("Model loaded successfully")
            
            if os.path.exists(classes_path):
                self.class_names = np.load(classes_path, allow_pickle=True)
                print(f"Classes loaded: {self.class_names}")
            
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("Scaler loaded")
            
            return self.model is not None and self.class_names is not None
        
        except Exception as e:
            print(f"Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_landmarks_from_frame(self, frame_array):
        """
        Extract hand landmarks from frame array
        
        Args:
            frame_array: np.array of shape (H, W, 3) in BGR format
            
        Returns:
            landmark_vector (63,) or None if no hand detected
        """
        try:
            frame_rgb = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
            detector = get_hands_detector()
            if not detector:
                return None
            results = detector.process(frame_rgb)
            
            if results.multi_hand_landmarks and len(results.multi_hand_landmarks) > 0:
                landmarks = results.multi_hand_landmarks[0]
                landmark_list = []
                for lm in landmarks.landmark:
                    landmark_list.extend([lm.x, lm.y, lm.z])
                return np.array(landmark_list)
            
            return None
        
        except Exception as e:
            print(f"Error extracting landmarks: {e}")
            return None
    
    def extract_landmarks_from_landmarks_data(self, landmarks_data):
        """
        Extract landmark vector from MediaPipe landmarks object
        
        Args:
            landmarks_data: MediaPipe hand landmarks
            
        Returns:
            landmark_vector (63,)
        """
        landmark_list = []
        for lm in landmarks_data.landmark:
            landmark_list.extend([lm.x, lm.y, lm.z])
        return np.array(landmark_list)
    
    def predict_sign(self, landmarks_vector, return_all_scores=False):
        """
        Predict FSL sign from landmark vector
        
        Args:
            landmarks_vector: np.array of shape (63,)
            return_all_scores: If True, return all class probabilities
            
        Returns:
            {
                'sign': str or None,
                'confidence': float,
                'threshold_met': bool,
                'all_scores': dict (if return_all_scores=True)
            }
        """
        if self.model is None or landmarks_vector is None:
            return {
                'sign': None,
                'confidence': 0.0,
                'threshold_met': False
            }
        
        try:
            # Type safety check
            if not isinstance(landmarks_vector, np.ndarray):
                landmarks_vector = np.array(landmarks_vector, dtype=np.float32)
            
            # Predict (Recursive safety)
            if landmarks_vector.shape != (63,):
                 print(f"Warning: Unexpected landmark shape {landmarks_vector.shape}")
            
            # Normalize
            if self.scaler:
                landmarks_normalized = self.scaler.transform([landmarks_vector])
            else:
                landmarks_normalized = np.array([landmarks_vector])
            
            # Predict with thread-safe lock
            with self.lock:
                predictions = self.model.predict(landmarks_normalized, verbose=0)[0]
            
            confidence = float(np.max(predictions))
            class_idx = int(np.argmax(predictions))
            
            result = {
                'sign': str(self.class_names[class_idx]) if confidence >= self.confidence_threshold else None,
                'confidence': confidence,
                'threshold_met': bool(confidence >= self.confidence_threshold),
                'all_scores': {}
            }
            
            if return_all_scores:
                for i, score in enumerate(predictions):
                    result['all_scores'][str(self.class_names[i])] = float(score)
            
            return result
        
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                'sign': None,
                'confidence': 0.0,
                'threshold_met': False
            }
    
    def get_smoothed_prediction(self, landmarks_vector, session_id='default', smoothing_window=3):
        """
        Get smoothed prediction using history
        
        Args:
            landmarks_vector: np.array of shape (63,)
            session_id: Session identifier for prediction tracking
            smoothing_window: Number of frames to consider
            
        Returns:
            Same as predict_sign
        """
        prediction = self.predict_sign(landmarks_vector)
        
        if prediction['sign']:
            self.prediction_history[session_id].append(prediction['sign'])
            if len(self.prediction_history[session_id]) > self.max_history:
                self.prediction_history[session_id].pop(0)
        else:
            self.prediction_history[session_id].clear()
        
        # Check if last N predictions agree
        history = self.prediction_history[session_id]
        if len(history) >= smoothing_window and len(set(history[-smoothing_window:])) == 1:
            return prediction
        
        if len(history) == 0:
            return {
                'sign': None,
                'confidence': prediction['confidence'],
                'threshold_met': False
            }
        
        return prediction
    
    def reset_history(self, session_id='default'):
        """Clear prediction history for a session"""
        if session_id in self.prediction_history:
            del self.prediction_history[session_id]
    
    def get_available_signs(self):
        """Get list of signs the model can recognize"""
        if self.class_names is None:
            return []
        return sorted(list(self.class_names))


class ProgressiveSignSequence:
    """Manages progressive sign checking for learning"""
    
    def __init__(self):
        """Initialize sequence manager"""
        self.sequence = []
        self.current_index = 0
        self.completed_signs = []
        self.consecutive_correct = 0
        self.required_consecutive = 1  # Instant detection - no need to hold
        self.current_confidence = 0.0
    
    def set_sequence(self, signs):
        """Set sequence of signs to learn
        
        Args:
            signs: List of sign letters
        """
        self.sequence = [s.upper() for s in signs]
        self.current_index = 0
        self.completed_signs = []
        self.consecutive_correct = 0
    
    @property
    def current_target(self):
        """Get the sign currently being learned"""
        if self.current_index < len(self.sequence):
            return self.sequence[self.current_index]
        return None

    def get_current_target(self):
        """Get the sign currently being learned (legacy method)"""
        return self.current_target
    
    def is_complete(self):
        """Check if all signs in sequence are completed"""
        return self.current_index >= len(self.sequence)
    
    def check_sign(self, detected_sign, confidence):
        """
        Check if detected sign is correct
        
        Args:
            detected_sign: Sign detected by model
            confidence: Confidence score
            
        Returns:
            {
                'is_correct': bool,
                'is_complete': bool,
                'message': str,
                'progress_percent': int,
                'completed': list,
                'target': str,
                'consecutive_count': int
            }
        """
        self.current_confidence = confidence
        expected = self.get_current_target()
        
        if expected is None:
            return {
                'is_correct': False,
                'is_complete': True,
                'message': '🎉 All signs completed!',
                'progress_percent': 100,
                'completed': self.completed_signs,
                'target': None,
                'consecutive_count': 0
            }
        
        # Robust comparison
        str_detected = str(detected_sign).strip().upper() if detected_sign else ""
        str_expected = str(expected).strip().upper() if expected else ""
        is_correct = (str_detected == str_expected)
        # print(f"Checking: '{str_detected}' vs '{str_expected}' -> {is_correct}")
        
        if is_correct:
            # Check confidence too, though usually pre-filtered by caller
            if confidence < 0.5: # Hard floor check
                return {
                    'is_correct': False,
                    'is_complete': False,
                    'message': 'Keep holding...',
                    'progress_percent': int((self.current_index / len(self.sequence)) * 100),
                    'completed': self.completed_signs,
                    'target': expected,
                    'consecutive_count': self.consecutive_correct,
                    'debug_info': f"Low confidence: {confidence}"
                }

            self.consecutive_correct += 1
            
            # Require 1 frame for instant response (but stable comparison)
            REQUIRED_FRAMES = 1
            
            if self.consecutive_correct >= REQUIRED_FRAMES:
                self.completed_signs.append(expected)
                self.current_index += 1
                self.consecutive_correct = 0
                
                if self.is_complete():
                    return {
                        'is_correct': True,
                        'is_complete': True,
                        'message': '🎉 Sequence complete! Excellent!',
                        'progress_percent': 100,
                        'completed': self.completed_signs,
                        'target': None,
                        'consecutive_count': 0
                    }
                else:
                    next_sign = self.get_current_target()
                    return {
                        'is_correct': True,
                        'is_complete': False,
                        'message': f'✅ Correct! Next: {next_sign}',
                        'progress_percent': int((self.current_index / len(self.sequence)) * 100),
                        'completed': self.completed_signs,
                        'target': next_sign,
                        'consecutive_count': 0
                    }
            else:
                return {
                    'is_correct': True,
                    'is_complete': False,
                    'message': f'✅ Good! {self.consecutive_correct}/{REQUIRED_FRAMES}',
                    'progress_percent': int((self.current_index / len(self.sequence)) * 100),
                    'completed': self.completed_signs,
                    'target': expected,
                    'consecutive_count': self.consecutive_correct
                }
        else:
            self.consecutive_correct = 0
            return {
                'is_correct': False,
                'is_complete': False,
                'message': f'❌ Try again (expected {expected})',
                'progress_percent': int((self.current_index / len(self.sequence)) * 100),
                'completed': self.completed_signs,
                'target': expected,
                'consecutive_count': 0,
                'debug_info': f"FAIL: '{str_detected}' != '{str_expected}'"
            }
    
    def advance(self):
        """
        Manually advance to the next sign (for external validation control)
        """
        if self.is_complete():
            return self.get_progress()
            
        # Add current target to completed if not already there
        current = self.get_current_target()
        if current and (len(self.completed_signs) == 0 or self.completed_signs[-1] != current):
             self.completed_signs.append(current)
        
        self.current_index += 1
        self.consecutive_correct = 0
        return self.get_progress()

    def skip_current(self):
        """
        Skip the current sign and move to the next
        
        Returns:
            Same structure as check_sign but marked as skipped
        """
        skipped_sign = self.get_current_target()
        
        if skipped_sign is None:
             return {
                'is_correct': False,
                'is_complete': True,
                'message': '🎉 All signs completed!',
                'progress_percent': 100,
                'completed': self.completed_signs,
                'target': None,
                'consecutive_count': 0,
                'sequence': self.sequence
            }
            
        self.completed_signs.append(skipped_sign)
        self.current_index += 1
        self.consecutive_correct = 0
        
        if self.is_complete():
            return {
                'is_correct': True, # Treat as success for progress
                'is_complete': True,
                'message': '🎉 Sequence complete!',
                'progress_percent': 100,
                'completed': self.completed_signs,
                'target': None,
                'consecutive_count': 0,
                'sequence': self.sequence
            }
        else:
            next_sign = self.get_current_target()
            return {
                'is_correct': True,
                'is_complete': False,
                'message': f'⏩ Skipped! Next: {next_sign}',
                'progress_percent': int((self.current_index / len(self.sequence)) * 100),
                'completed': self.completed_signs,
                'target': next_sign,
                'consecutive_count': 0,
                'sequence': self.sequence
            }
    
    def get_progress(self):
        """Get progress information"""
        return {
            'current_target': self.get_current_target(),
            'completed': self.completed_signs,
            'progress_percent': int((self.current_index / len(self.sequence)) * 100) if self.sequence else 0,
            'is_complete': self.is_complete(),
            'sequence': self.sequence
        }


# Global inference engine instance
_inference_engine = None


def get_inference_engine():
    """Get or create global inference engine"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = FSLInferenceEngine()
    return _inference_engine


# Required import for frame processing
try:
    import cv2
except ImportError:
    cv2 = None
    print("Warning: OpenCV not available for frame processing")
