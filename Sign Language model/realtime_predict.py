"""
Filipino Sign Language (FSL) Real-Time Predictor
Captures live video from webcam and predicts FSL signs using trained model.

Features:
- Real-time hand detection and landmark extraction
- Model inference with confidence scoring
- Progressive sign checking (A→B→C sequence)
- Smooth predictions with frame averaging
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import pickle
import tensorflow as tf
from tensorflow import keras
from collections import deque


# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils


class FSLPredictor:
    """Real-time FSL sign predictor"""
    
    def __init__(self, model_dir='models'):
        """
        Initialize predictor
        
        Args:
            model_dir: Directory containing trained model files
        """
        self.model_dir = model_dir
        self.model = None
        self.class_names = None
        self.scaler = None
        self.load_model()
        
        # Prediction smoothing
        self.prediction_buffer = deque(maxlen=5)
        self.confidence_threshold = 0.6
    
    def load_model(self):
        """Load trained model and preprocessor"""
        print("📂 Loading model...")
        
        model_path = os.path.join(self.model_dir, 'fsl_model.h5')
        classes_path = os.path.join(self.model_dir, 'fsl_model_classes.npy')
        scaler_path = os.path.join(self.model_dir, 'landmark_scaler.pkl')
        
        try:
            if os.path.exists(model_path):
                self.model = keras.models.load_model(model_path)
                print(f"  ✅ Model loaded")
            else:
                print(f"  ❌ Model not found at {model_path}")
                return False
            
            if os.path.exists(classes_path):
                self.class_names = np.load(classes_path, allow_pickle=True)
                print(f"  ✅ Classes loaded: {list(self.class_names)}")
            else:
                print(f"  ❌ Class names not found")
                return False
            
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print(f"  ✅ Scaler loaded")
            else:
                print(f"  ⚠️  Scaler not found, predictions may be inaccurate")
            
            return True
        
        except Exception as e:
            print(f"  ❌ Error loading model: {e}")
            return False
    
    def extract_landmarks(self, frame):
        """Extract 21 hand landmarks from frame"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) > 0:
            landmarks = results.multi_hand_landmarks[0]
            # Convert to 63-element array
            landmark_list = []
            for lm in landmarks.landmark:
                landmark_list.extend([lm.x, lm.y, lm.z])
            return np.array(landmark_list), landmarks
        
        return None, None
    
    def predict(self, landmarks_array):
        """Predict FSL sign from landmarks"""
        if landmarks_array is None or self.model is None:
            return None, 0.0
        
        try:
            # Normalize
            if self.scaler:
                landmarks_normalized = self.scaler.transform([landmarks_array])
            else:
                landmarks_normalized = np.array([landmarks_array])
            
            # Predict
            predictions = self.model.predict(landmarks_normalized, verbose=0)
            confidence = np.max(predictions)
            class_idx = np.argmax(predictions)
            
            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                return None, confidence
            
            return self.class_names[class_idx], confidence
        
        except Exception as e:
            print(f"Prediction error: {e}")
            return None, 0.0
    
    def get_smoothed_prediction(self, landmarks_array):
        """Get smoothed prediction using buffer"""
        prediction, confidence = self.predict(landmarks_array)
        
        if prediction:
            self.prediction_buffer.append(prediction)
        else:
            self.prediction_buffer.clear()
        
        if len(self.prediction_buffer) >= 3:
            # Check if last 3 predictions are same
            if len(set(self.prediction_buffer)) == 1:
                return self.prediction_buffer[0], confidence
        
        return None, confidence


class ProgressiveSignChecker:
    """Manages progressive sign checking (A→B→C sequence)"""
    
    def __init__(self):
        """Initialize checker"""
        self.sequence = []
        self.current_index = 0
        self.completed = []
        self.consecutive_correct = 0
        self.required_consecutive = 3  # Must recognize sign 3 times to advance
    
    def set_sequence(self, signs):
        """Set the sequence to check
        
        Args:
            signs: List of sign letters (e.g., ['A', 'B', 'C'])
        """
        self.sequence = [s.upper() for s in signs]
        self.current_index = 0
        self.completed = []
        self.consecutive_correct = 0
        print(f"📋 Sequence set: {' → '.join(self.sequence)}")
    
    def get_current_expected(self):
        """Get the currently expected sign"""
        if self.current_index < len(self.sequence):
            return self.sequence[self.current_index]
        return None
    
    def check_sign(self, detected_sign):
        """Check if detected sign matches expected
        
        Args:
            detected_sign: The sign detected by model
            
        Returns:
            (is_correct, is_complete, progress_message)
        """
        expected = self.get_current_expected()
        
        if expected is None:
            return False, True, "✅ Sequence complete!"
        
        is_correct = (detected_sign == expected)
        
        if is_correct:
            self.consecutive_correct += 1
            
            if self.consecutive_correct >= self.required_consecutive:
                self.completed.append(expected)
                self.current_index += 1
                self.consecutive_correct = 0
                
                if self.current_index >= len(self.sequence):
                    return True, True, "🎉 All signs completed!"
                else:
                    next_sign = self.sequence[self.current_index]
                    return True, False, f"✅ Correct! Next: {next_sign}"
            else:
                remaining = self.required_consecutive - self.consecutive_correct
                return True, False, f"✅ {self.consecutive_correct}/{self.required_consecutive} correct"
        else:
            self.consecutive_correct = 0
            return False, False, f"❌ Wrong sign (expected {expected})"
    
    def get_progress(self):
        """Get progress as percentage"""
        if len(self.sequence) == 0:
            return 0
        return int((self.current_index / len(self.sequence)) * 100)


def main():
    """Main real-time prediction loop"""
    print("\n" + "="*60)
    print("Filipino Sign Language (FSL) Real-Time Predictor")
    print("="*60)
    print("\nControls:")
    print("  SPACE      : Set sequence (enter letters)")
    print("  Q          : Quit")
    print("="*60 + "\n")
    
    # Initialize
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    predictor = FSLPredictor()
    checker = ProgressiveSignChecker()
    
    if predictor.model is None:
        print("❌ Failed to load model")
        cap.release()
        return
    
    # Set default sequence for demo - ALL 26 LETTERS
    checker.set_sequence(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read from camera")
                break
            
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Extract landmarks
            landmarks_array, landmarks = predictor.extract_landmarks(frame)
            
            # Draw hand skeleton
            if landmarks:
                try:
                    # Try new MediaPipe API
                    mp_drawing.draw_landmarks(
                        frame,
                        mp.solutions.hands.HandLandmarkList(landmark=landmarks.landmark),
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                except AttributeError:
                    # Fallback for older MediaPipe API - draw manually
                    h, w = frame.shape[:2]
                    
                    # Draw landmarks
                    for lm in landmarks.landmark:
                        x, y = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                    
                    # Draw connections
                    connections = [
                        [0, 1], [1, 2], [2, 3], [3, 4],
                        [0, 5], [5, 6], [6, 7], [7, 8],
                        [0, 9], [9, 10], [10, 11], [11, 12],
                        [0, 13], [13, 14], [14, 15], [15, 16],
                        [0, 17], [17, 18], [18, 19], [19, 20],
                        [5, 9], [9, 13], [13, 17]
                    ]
                    
                    for start_idx, end_idx in connections:
                        start = landmarks.landmark[start_idx]
                        end = landmarks.landmark[end_idx]
                        x1, y1 = int(start.x * w), int(start.y * h)
                        x2, y2 = int(end.x * w), int(end.y * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # Get prediction
                prediction, confidence = predictor.get_smoothed_prediction(landmarks_array)
                
                if prediction:
                    is_correct, is_complete, message = checker.check_sign(prediction)
                    
                    # Draw prediction info
                    color = (0, 255, 0) if is_correct else (0, 0, 255)
                    cv2.rectangle(frame, (10, 10), (600, 150), color, -1)
                    cv2.putText(frame, f"Detected: {prediction}", (20, 50), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
                    cv2.putText(frame, f"Confidence: {confidence:.2f}", (20, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(frame, message, (20, 130), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw sequence info
            expected = checker.get_current_expected()
            progress = checker.get_progress()
            
            cv2.rectangle(frame, (10, h-130), (400, h-10), (100, 100, 100), -1)
            cv2.putText(frame, f"Expected: {expected or 'NONE'}", (20, h-90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, f"Completed: {' → '.join(checker.completed)}", (20, h-50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Progress: {progress}%", (20, h-15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('FSL Real-Time Predictor', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                seq = input("Enter sequence (e.g., ABC): ").upper()
                if seq:
                    checker.set_sequence(list(seq))
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        
        print("\n" + "="*60)
        print("✅ Real-time prediction ended")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
