#!/usr/bin/env python3
"""
Camera Troubleshooting Script
Diagnoses camera and hand detection issues
"""

import cv2
import mediapipe as mp

print("\n" + "="*60)
print("📷 CAMERA TROUBLESHOOTING")
print("="*60)

# Test 1: Camera Access
print("\n1️⃣  Testing Camera Access...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ ERROR: Cannot open camera!")
    print("   - Check if camera is connected")
    print("   - Close other apps using camera (Teams, Discord, etc.)")
    print("   - Try unplugging and replugging the camera")
    exit(1)

print("✅ Camera opened successfully")

# Test 2: Camera Properties
print("\n2️⃣  Camera Properties:")
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"   Resolution: {int(width)}x{int(height)}")
print(f"   FPS: {fps}")

# Test 3: Frame Capture
print("\n3️⃣  Testing Frame Capture...")
ret, frame = cap.read()
if not ret:
    print("❌ ERROR: Cannot read frames from camera!")
    print("   - Camera may be busy")
    print("   - Try restarting computer")
    cap.release()
    exit(1)

print(f"✅ Frame captured: {frame.shape}")

# Test 4: MediaPipe Initialization
print("\n4️⃣  Testing MediaPipe Hands...")
try:
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    print("✅ MediaPipe Hands initialized")
except Exception as e:
    print(f"❌ ERROR initializing MediaPipe: {e}")
    cap.release()
    exit(1)

# Test 5: Hand Detection
print("\n5️⃣  Testing Hand Detection (5 frames)...")
detected_count = 0

for i in range(5):
    ret, frame = cap.read()
    if not ret:
        print(f"❌ Cannot read frame {i+1}")
        break
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    
    if results.multi_hand_landmarks:
        detected_count += 1
        print(f"   Frame {i+1}: ✅ Hand detected ({len(results.multi_hand_landmarks[0].landmark)} landmarks)")
    else:
        print(f"   Frame {i+1}: ⚠️  No hand detected")

cap.release()
hands.close()

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"✅ Camera: Working")
print(f"✅ Frame Capture: Working")
print(f"✅ MediaPipe: Working")
print(f"✅ Hand Detection: {detected_count}/5 frames detected hand")

if detected_count >= 3:
    print("\n✅ Everything looks good! Camera and hand detection working.")
    print("\nYou can now run: python dataset_collector.py")
elif detected_count > 0:
    print("\n⚠️  Hand detection is working but inconsistent.")
    print("   Tips:")
    print("   - Ensure good lighting")
    print("   - Keep hand clearly visible in camera frame")
    print("   - Move hand slowly and steadily")
else:
    print("\n⚠️  Hand detection not working in test.")
    print("   Tips:")
    print("   - Ensure hand is visible in front of camera")
    print("   - Check lighting (not too dark, not too bright)")
    print("   - Move hand closer to camera")
    print("   - Try again with different hand position")

print("="*60 + "\n")
