"""
FSL Model Trainer
Trains a neural network to classify hand signs from landmark data.

The model:
- Loads CSV files with 63 features (21 landmarks × 3 coordinates)
- Normalizes the data using StandardScaler
- Trains a deep neural network using TensorFlow/Keras
- Saves the trained model and preprocessing parameters
"""

import os
import csv
import numpy as np
import pickle
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
import matplotlib.pyplot as plt


class FSLModelTrainer:
    """Trains FSL recognition model"""
    
    def __init__(self, dataset_dir='datasets/FSL_Landmarks', output_dir='models'):
        """
        Initialize trainer
        
        Args:
            dataset_dir: Directory containing CSV files for each sign
            output_dir: Directory to save trained models
        """
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.X = None
        self.y = None
        self.class_names = None
        self.scaler = StandardScaler()
        self.model = None
        self.history = None
    
    def load_dataset(self):
        """Load landmark data from CSV files"""
        print("Loading dataset...")
        
        X = []
        y = []
        class_names = []
        
        # Load each CSV file
        csv_files = sorted([f for f in os.listdir(self.dataset_dir) if f.endswith('.csv')])
        
        if not csv_files:
            print(f"No CSV files found in {self.dataset_dir}")
            return False
        
        for csv_file in csv_files:
            sign_name = csv_file.replace('.csv', '')
            class_names.append(sign_name)
            
            csv_path = os.path.join(self.dataset_dir, csv_file)
            
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    
                    for row in reader:
                        if len(row) == 63:  # 21 landmarks × 3 coordinates
                            # Original sample
                            original_sample = [float(val) for val in row]
                            X.append(original_sample)
                            y.append(len(class_names) - 1)
                            
                            # Augmented sample (Mirrored X-axis)
                            # This generates a "Right Hand" version from "Left Hand" data (and vice-versa)
                            mirrored_sample = list(original_sample)
                            for i in range(0, 63, 3):  # Indices 0, 3, 6... are X coordinates
                                mirrored_sample[i] = 1.0 - mirrored_sample[i]
                                
                            X.append(mirrored_sample)
                            y.append(len(class_names) - 1)
                
                count = len([val for val in y if val == len(class_names) - 1])
                print(f"  {sign_name}: {count} samples (Original + Mirrored)")
            
            except Exception as e:
                print(f"  Error loading {csv_file}: {e}")
                continue
        
        if not X:
            print("No data loaded!")
            return False
        
        self.X = np.array(X)
        self.y = np.array(y)
        self.class_names = np.array(class_names)
        
        print(f"\nDataset loaded: {len(X)} samples, {len(class_names)} classes")
        print(f"   Classes: {', '.join(class_names)}")
        return True
    
    def preprocess_data(self):
        """Normalize landmark data"""
        print("\nPreprocessing data...")
        
        # Normalize
        self.X = self.scaler.fit_transform(self.X)
        print("  Data normalized")
        
        # Save scaler parameters for inference
        scaler_path = os.path.join(self.output_dir, 'landmark_scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        print(f"  Scaler saved to {scaler_path}")
    
    def build_model(self, num_classes):
        """Build neural network model"""
        print("\nBuilding model...")
        
        model = models.Sequential([
            # Input: 63 features (21 landmarks × 3 coordinates)
            layers.Input(shape=(63,)),
            
            # Dense layers with dropout for regularization
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            layers.Dense(32, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            layers.Dense(16, activation='relu'),
            
            # Output: classification layer
            layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print("  Model architecture:")
        model.summary()
        
        self.model = model
    
    def train_model(self, epochs=50, batch_size=32, validation_split=0.2):
        """Train the model"""
        print(f"\nTraining model ({epochs} epochs)...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            self.X, self.y, test_size=0.2, random_state=42, stratify=self.y
        )
        
        # Early stopping callback
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            verbose=1
        )
        
        # Train
        self.history = self.model.fit(
            X_train, y_train,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop],
            verbose=1
        )
        
        # Evaluate
        print("\nEvaluating model...")
        y_pred = np.argmax(self.model.predict(X_test, verbose=0), axis=1)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"  Test Accuracy: {accuracy:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=self.class_names))
        
        return accuracy
    
    def save_model(self, model_name='fsl_model'):
        """Save trained model and metadata"""
        print("\nSaving model...")
        
        # Save model
        model_path = os.path.join(self.output_dir, f'{model_name}.h5')
        self.model.save(model_path)
        print(f"  Model saved to {model_path}")
        
        # Save class names
        class_names_path = os.path.join(self.output_dir, f'{model_name}_classes.npy')
        np.save(class_names_path, self.class_names)
        print(f"  Class names saved to {class_names_path}")
        
        # Save metadata
        metadata = {
            'num_classes': len(self.class_names),
            'class_names': self.class_names.tolist(),
            'feature_size': 63,
            'model_type': 'Dense Neural Network'
        }
        
        metadata_path = os.path.join(self.output_dir, f'{model_name}_metadata.npy')
        np.save(metadata_path, metadata, allow_pickle=True)
        print(f"  Metadata saved to {metadata_path}")
    
    def plot_history(self):
        """Plot training history"""
        if self.history is None:
            return
        
        plt.figure(figsize=(12, 4))
        
        # Accuracy
        plt.subplot(1, 2, 1)
        plt.plot(self.history.history['accuracy'], label='Train Accuracy')
        plt.plot(self.history.history['val_accuracy'], label='Val Accuracy')
        plt.title('Model Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.legend()
        plt.grid()
        
        # Loss
        plt.subplot(1, 2, 2)
        plt.plot(self.history.history['loss'], label='Train Loss')
        plt.plot(self.history.history['val_loss'], label='Val Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'training_history.png'))
        print("\n  Training history plot saved")
        plt.show()


def main():
    """Main training pipeline"""
    print("\n" + "="*60)
    print("Filipino Sign Language (FSL) Model Trainer")
    print("="*60)
    
    # Initialize trainer
    trainer = FSLModelTrainer(
        dataset_dir='datasets/FSL_Landmarks',
        output_dir='models'
    )
    
    # Load dataset
    if not trainer.load_dataset():
        print("Failed to load dataset")
        return
    
    # Preprocess
    trainer.preprocess_data()
    
    # Build model
    trainer.build_model(num_classes=len(trainer.class_names))
    
    # Train
    accuracy = trainer.train_model(epochs=50, batch_size=32)
    
    # Save
    trainer.save_model('fsl_model')
    
    # Plot
    trainer.plot_history()
    
    print("\n" + "="*60)
    print("Training completed successfully!")
    print("="*60)
    print(f"\nModel files saved in: {trainer.output_dir}")
    print(f"  - fsl_model.h5 (trained model)")
    print(f"  - fsl_model_classes.npy (class names)")
    print(f"  - fsl_model_metadata.npy (metadata)")
    print(f"  - landmark_scaler.pkl (normalization parameters)")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
