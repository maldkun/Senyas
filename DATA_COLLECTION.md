# User Data Collection Documentation

This document outlines all data collected by the Sign Language Learning Web Application.

## 1. User Account Data

### Account Registration
- **Email Address**: User's email (stored as plain text, used for login)
- **Password**: Hashed using Werkzeug security (never stored in plain text)
- **First Name**: User's display name
- **Registration Timestamp**: Automatic (account creation date)

### Account Progress
- **FSL Progress**: Integer (0-5) tracking completed alphabet parts
- **Dynamic Difficulty Unlocks**:
  - Alphabets unlocked status
  - Words unlocked status
  - Phrases unlocked status

### User Feedback
- **Feedback Text**: User-submitted feedback messages
- **Submission Timestamp**: When feedback was sent

## 2. Static Difficulty Data

### Session Data (DynamicSession Table)
- **Session ID**: Unique identifier
- **Course**: "alphabets" (static mode)
- **Mode**: "static"
- **Start/End Timestamps**: When session began/completed
- **Total Signs**: Number of signs in the session (5 per part)
- **Correct/Incorrect Counts**: Performance metrics
- **Final Study Time**: Fixed at 0 seconds (static mode)
- **Final Threshold**: Fixed at 50% (static mode)
- **EXP Earned**: Gamification points awarded
- **Level Changes**: Before/after levels and ups occurred

### Attempt Data (SignAttempt Table)
For each individual sign attempt:
- **Session ID**: Links to parent session
- **Sign ID**: Which letter was attempted (A, B, C, etc.)
- **Course**: "alphabets"
- **Correct/Incorrect**: Boolean result
- **AI Detected Sign**: What the AI model predicted
- **AI Confidence**: Confidence score (0.0-1.0)
- **Validation Threshold**: 50% (static mode)
- **Study Time Used**: How long user studied the sign
- **Attempt Timestamp**: When attempt occurred
- **EXP Earned**: Points awarded for this attempt

### Statistics Updates (UserSignStats Table)
Aggregated per-sign performance:
- **Sign ID**: Individual letter
- **Course**: "alphabets"
- **Total Attempts**: Running count
- **Correct Count**: Running correct count
- **Last Practiced**: Most recent attempt timestamp
- **Average Confidence**: Mean confidence across attempts
- **Last 5 Attempts**: JSON array of recent boolean results

## 3. Dynamic Difficulty Data

### Session Data (DynamicSession Table)
- **Session ID**: Unique identifier
- **Course**: "alphabets" (dynamic mode)
- **Mode**: "dynamic"
- **Start/End Timestamps**: Session timing
- **Total Signs**: 15 signs per session
- **Correct/Incorrect Counts**: Performance tracking
- **Final Study Time**: Adaptive (starts at 5s, adjusts based on performance)
- **Final Threshold**: Adaptive (starts at 70%, adjusts based on performance)
- **EXP Earned**: Session completion rewards
- **Level Changes**: Gamification progression

### Attempt Data (SignAttempt Table)
Enhanced tracking per attempt:
- **Session ID**: Parent session link
- **Sign ID**: Target sign
- **Course**: "alphabets"
- **Correct/Incorrect**: Validation result
- **AI Detected Sign**: Model prediction
- **AI Confidence**: Prediction confidence
- **Validation Threshold**: Current adaptive threshold
- **Study Time Used**: Actual study duration
- **Study Time Limit**: Maximum allowed study time
- **Current Threshold**: Threshold at attempt time
- **Batch Information**: Which batch (0-5) and position
- **Attempt Timestamp**: Precise timing
- **EXP Earned**: Per-attempt rewards

### Statistics Updates (UserSignStats Table)
Same as static mode but with dynamic thresholds affecting confidence tracking.

## 4. AI-Driven Difficulty Data

### Session Data (DynamicSession Table)
- **Session ID**: Unique identifier
- **Course**: "alphabets_ai" (AI mode)
- **Mode**: "ai"
- **Start/End Timestamps**: Session boundaries
- **Total Signs**: 15 personalized signs
- **Correct/Incorrect Counts**: Performance metrics
- **Final Study Time**: AI-calculated optimal time
- **Final Threshold**: AI-calculated optimal threshold
- **EXP Earned**: Enhanced rewards for AI mode
- **Level Changes**: Advanced progression

### Attempt Data (SignAttempt Table)
Comprehensive AI-enhanced tracking:
- **Session ID**: AI session link
- **Sign ID**: AI-selected target sign
- **Course**: "alphabets_ai"
- **Correct/Incorrect**: Sustained-hold validation
- **AI Detected Sign**: Real-time predictions
- **AI Confidence**: Frame-by-frame confidence
- **Validation Threshold**: AI-calculated per-sign
- **Study Time Used**: Actual study duration
- **Study Time Limit**: AI-recommended limit
- **Current Threshold**: Dynamic threshold
- **Batch Information**: AI-organized batches (Challenging/Moderate/Easy)
- **Attempt Timestamp**: High-precision timing
- **EXP Earned**: AI-enhanced rewards

### Enhanced Statistics (UserSignStats Table)
AI-specific performance tracking:
- **Sign ID**: AI-selected signs
- **Course**: "alphabets_ai"
- **Total Attempts**: Comprehensive counting
- **Correct Count**: Success tracking
- **Last Practiced**: Recent activity
- **Average Confidence**: AI confidence analysis
- **Last 5 Attempts**: Detailed performance history

### AI-Specific Data Collection
- **Performance History**: Used for difficulty adaptation
- **Confidence Patterns**: Learning user confidence thresholds
- **Study Time Preferences**: Optimal timing per user
- **Sign Difficulty Assessment**: Individual sign performance analysis

## 5. Gamification & Achievement Data

### User Progress (UserProgress Table)
- **Total EXP**: Cumulative experience points
- **Current Level**: User's current level (1-10)
- **Streak Tracking**: Current/longest daily practice streaks
- **Last Practice Date**: Most recent activity
- **Session Counters**: Total completed sessions
- **Sign Counters**: Total attempts and correct answers
- **Timestamps**: Creation and update times

### Achievement System (UserAchievement Table)
- **Achievement ID**: Which achievement unlocked
- **Unlock Timestamp**: When earned
- **Showcase Status**: If displayed on profile

### EXP Transactions (EXPTransaction Table)
Detailed audit log:
- **Amount**: EXP earned
- **Source**: What activity earned it
- **Description**: Human-readable explanation
- **Linked Records**: Session/attempt IDs
- **Timestamp**: When earned

## 6. Data Not Stored

### Ephemeral Data (Not Persisted)
- **Camera/Video Feed**: Real-time video processed but not stored
- **Raw Landmark Data**: Used for inference but discarded after processing
- **Intermediate Predictions**: Temporary model outputs not saved
- **Session State**: In-memory sequences cleared after use

### Privacy Considerations
- **No Personal Images**: Video feed processed in real-time only
- **No Location Data**: No GPS or location tracking
- **No Third-Party Sharing**: All data stays on user's device/server
- **Account Isolation**: Each user has completely separate data

## 7. Data Retention & Deletion

- **Account Deletion**: Removes all user data
- **Session History**: Retained for progress tracking
- **Automatic Cleanup**: Old temporary data removed
- **Backup Considerations**: Database backups may retain historical data

## 8. Data Usage

### Primary Uses
- **Personalization**: AI adapts difficulty to user performance
- **Progress Tracking**: Visual feedback on learning journey
- **Gamification**: Motivation through levels and achievements
- **Analytics**: Performance insights for improvement

### Technical Uses
- **Model Training**: Aggregated anonymized data could improve AI (not currently implemented)
- **System Optimization**: Performance metrics for app improvements
- **User Experience**: Personalized learning paths

---

**Last Updated**: March 16, 2026
**Data Controller**: Sign Language Learning Application
**Contact**: For data deletion requests, contact the application administrator</content>
<parameter name="filePath">c:\Users\User\Desktop\Senyas Web\DATA_COLLECTION.md