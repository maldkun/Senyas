"""
FSL Dataset Collector
Captures hand landmarks from webcam and saves them to CSV files for training.

Usage:
    - Press letter key (A-Z) to start capturing that sign
    - Hold your hand in the sign position
    - Press 'SPACE' to save the captured frame
    - Press 'Q' to quit
    - Press 'DELETE' to remove last frame (undo)
"""

import cv2
import mediapipe as mp
import numpy as np
import os
import csv
from collections import deque
from datetime import datetime

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

class FSLDatasetCollector:
    """Collects and saves FSL hand landmark data"""
    
    def __init__(self, dataset_dir='datasets/FSL_Landmarks'):
        """
        Initialize the dataset collector
        
        Args:
            dataset_dir: Directory where CSV files will be saved
        """
        self.dataset_dir = dataset_dir
        os.makedirs(dataset_dir, exist_ok=True)
        
        self.current_sign = None
        self.current_landmarks = deque(maxlen=30)  # Store up to 30 frames
        self.csv_path = None
        self.frame_count = 0
        self.total_saved = 0
        self.target_samples = 375  # Target 350-400 samples per letter
        
        # Load existing data counts
        self.sign_counts = self._get_sign_counts()
        
    def _get_sign_counts(self):
        """Get current count of samples per sign"""
        counts = {}
        for file in os.listdir(self.dataset_dir):
            if file.endswith('.csv'):
                sign = file.replace('.csv', '')
                try:
                    with open(os.path.join(self.dataset_dir, file), 'r') as f:
                        counts[sign] = sum(1 for line in f) - 1  # -1 for header
                except:
                    counts[sign] = 0
        return counts
    
    def set_current_sign(self, sign_letter):
        """Set the current sign to collect"""
        self.current_sign = sign_letter.upper()
        self.current_landmarks.clear()
        self.frame_count = 0
        self.csv_path = os.path.join(self.dataset_dir, f'{self.current_sign}.csv')
        
        # Initialize CSV if it doesn't exist
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Header: 21 landmarks × 3 coordinates (x, y, z)
                headers = []
                for i in range(21):
                    headers.extend([f'x{i}', f'y{i}', f'z{i}'])
                writer.writerow(headers)
        
        count = self.sign_counts.get(self.current_sign, 0)
        remaining = max(0, self.target_samples - count)
        print(f"\n📝 Collecting sign: {self.current_sign}")
        print(f"   Current samples: {count}/{self.target_samples}")
        if remaining > 0:
            print(f"   Samples needed: {remaining}")
        else:
            print(f"   ✅ Target reached! (You can collect more if desired)")
        print(f"   Status: Ready to record (show hand gesture and press SPACE to save)")
    
    def extract_landmarks(self, frame):
        """Extract hand landmarks from frame"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) > 0:
            landmarks = results.multi_hand_landmarks[0]
            # Convert to 63-element array (21 landmarks × 3 coordinates)
            landmark_list = []
            for lm in landmarks.landmark:
                landmark_list.extend([lm.x, lm.y, lm.z])
            return np.array(landmark_list), landmarks, results.multi_hand_landmarks
        
        return None, None, None
    
    def save_landmarks(self):
        """Save accumulated landmarks to CSV"""
        if not self.current_sign or len(self.current_landmarks) == 0:
            return False
        
        # Average landmarks across frames for stability
        avg_landmarks = np.mean(list(self.current_landmarks), axis=0)
        
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(avg_landmarks)
        
        self.sign_counts[self.current_sign] = self.sign_counts.get(self.current_sign, 0) + 1
        self.total_saved += 1
        self.current_landmarks.clear()
        self.frame_count = 0
        
        return True
    
    def undo_last_frame(self):
        """Remove the last saved frame (undo)"""
        if not self.current_sign:
            print("⚠️  Please select a sign first (press A-Z)")
            return False
        
        csv_path = os.path.join(self.dataset_dir, f'{self.current_sign}.csv')
        
        try:
            with open(csv_path, 'r') as f:
                lines = f.readlines()
            
            if len(lines) > 1:  # More than header
                with open(csv_path, 'w') as f:
                    f.writelines(lines[:-1])
                
                # Recount the lines to get accurate count
                with open(csv_path, 'r') as f:
                    new_count = sum(1 for line in f) - 1  # -1 for header
                
                self.sign_counts[self.current_sign] = new_count
                print(f"↩️  Deleted last sample. Remaining: {new_count}")
                return True
            else:
                print("⚠️  No samples to delete")
        except Exception as e:
            print(f"❌ Error deleting sample: {e}")
        
        return False
    
    def clear_all_data(self):
        """Clear all data for current sign"""
        if not self.current_sign:
            print("⚠️  Please select a sign first (press A-Z)")
            return False
        
        csv_path = os.path.join(self.dataset_dir, f'{self.current_sign}.csv')
        
        try:
            # Delete the file completely
            if os.path.exists(csv_path):
                os.remove(csv_path)
                self.sign_counts[self.current_sign] = 0
                print(f"🗑️  Cleared all data for {self.current_sign}")
                return True
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
        
        return False
    
    def add_landmark_frame(self, landmarks_array):
        """Add landmark frame to buffer"""
        if landmarks_array is not None:
            self.current_landmarks.append(landmarks_array)
            self.frame_count += 1


def main():
    """Main function for collecting FSL dataset"""
    print("\n" + "="*60)
    print("Filipino Sign Language (FSL) Dataset Collector")
    print("="*60)
    print("\nControls:")
    print("  A-Z        : Select sign to collect")
    print("  SPACE      : Save current frame/gesture")
    print("  DELETE     : Remove last saved sample")
    print("  BACKSPACE  : Clear ALL data for current sign")
    print("  ESC        : Quit")
    print("\nInstructions:")
    print("  1. Press a letter (A-Z) to start collecting that sign")
    print("  2. Show the hand gesture clearly in front of the camera")
    print("  3. Press SPACE to record (hold position steady)")
    print("  4. Repeat steps 2-3 to collect multiple samples")
    print("="*60 + "\n")
    
    # Initialize camera and collector
    print("🎬 Initializing camera...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("❌ ERROR: Cannot open camera!")
        print("   - Check if camera is connected")
        print("   - Check if camera is not in use by another app")
        print("   - Try restarting the script")
        return
    
    print("✅ Camera initialized successfully\n")
    
    collector = FSLDatasetCollector()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read from camera - reconnecting...")
                cap.release()
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                continue
            
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Extract landmarks
            landmarks_array, landmarks, multi_hand_landmarks = collector.extract_landmarks(frame)
            
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
                
                # Add landmark to buffer if hand detected
                if collector.current_sign:
                    collector.add_landmark_frame(landmarks_array)
            
            # Display info
            cv2.rectangle(frame, (10, 10), (400, 100), (200, 200, 200), -1)
            current_count = collector.sign_counts.get(collector.current_sign or 'X', 0)
            cv2.putText(frame, f"Current Sign: {collector.current_sign or 'NONE'}", 
                       (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(frame, f"Saved Samples: {current_count}/{collector.target_samples}", 
                       (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            cv2.imshow('FSL Dataset Collector', frame)
            
            # Handle keyboard input with timeout
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC key - Quit
                print("\n✅ Dataset collection completed!")
                break
            elif key == ord(' '):  # SPACE - Save
                if collector.current_sign and collector.frame_count > 0:
                    if collector.save_landmarks():
                        print(f"✅ Saved {collector.current_sign}: Sample #{collector.sign_counts[collector.current_sign]}")
                    else:
                        print("⚠️  No frames to save")
                else:
                    if not collector.current_sign:
                        print("⚠️  Please select a sign first (press A-Z)")
                    else:
                        print("⚠️  No hand detected - try again")
            elif key == 255 or key == 46:  # DELETE key (255 in some systems, 46 in others) - Undo
                if collector.undo_last_frame():
                    pass
            elif key == 8:  # BACKSPACE key - Clear all data for current sign
                collector.clear_all_data()
            elif ord('A') <= key <= ord('Z'):  # A-Z keys
                sign_letter = chr(key)
                collector.set_current_sign(sign_letter)
            elif ord('a') <= key <= ord('z'):  # lowercase a-z
                sign_letter = chr(key).upper()
                collector.set_current_sign(sign_letter)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n" + "="*60)
        print("Dataset Summary:")
        print("="*60)
        for sign in sorted(collector.sign_counts.keys()):
            print(f"  {sign}: {collector.sign_counts[sign]} samples")
        print(f"\nTotal samples collected: {sum(collector.sign_counts.values())}")
        print(f"Saved in: {collector.dataset_dir}")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
