"""
Filipino Sign Language Recognition API
Loads trained model and provides REST endpoints for predictions
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import cv2
from tensorflow import keras
from tensorflow.python.keras.layers import InputLayer
import os
import uuid
from werkzeug.utils import secure_filename
from fsl_inference import get_inference_engine, ProgressiveSignSequence

# Initialize inference engine
inference_engine = get_inference_engine()

# Store active sequences: session_id -> ProgressiveSignSequence
active_sequences = {}


# Custom object scope to handle older model format compatibility
class CompatibleInputLayer(InputLayer):
    """InputLayer that accepts both batch_shape and batch_input_shape for compatibility"""

    def __init__(self, **kwargs):
        # Convert batch_shape to batch_input_shape if needed
        if 'batch_shape' in kwargs:
            kwargs['batch_input_shape'] = kwargs.pop('batch_shape')
        super().__init__(**kwargs)


app = Flask(__name__)
CORS(app)  # Enable CORS for web requests

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
IMG_SIZE = 128

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load model and class names
print("Loading trained model...")

# Get absolute path to model files
current_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(current_dir, 'models')
model_path = os.path.join(models_dir, 'fsl_model.h5')
class_names_path = os.path.join(models_dir, 'fsl_model_classes.npy')

print(f"Looking for model at: {model_path}")
print(f"Looking for classes at: {class_names_path}")

model = None
class_names = None

try:
    if not os.path.exists(model_path):
        print(f"❌ Model file not found at: {model_path}")
        print(f"   Files in directory: {os.listdir(current_dir)}")
    else:
        # Use compile=False and safe_mode=False to handle version incompatibility
        try:
            model = keras.models.load_model(model_path, compile=False, safe_mode=False)
            print(f"✅ Model loaded successfully!")
        except Exception as e1:
            print(f"⚠️ First load attempt failed: {e1}")
            print("Trying alternative loading method...")
            # Try loading with custom objects
            custom_objects = {'InputLayer': CompatibleInputLayer}
            model = keras.models.load_model(
                model_path, custom_objects=custom_objects, compile=False, safe_mode=False)
            print(f"✅ Model loaded successfully with custom objects!")

    if not os.path.exists(class_names_path):
        print(f"❌ Class names file not found at: {class_names_path}")
    else:
        class_names = np.load(class_names_path, allow_pickle=True)
        print(f"✅ Classes loaded: {list(class_names)}")

except Exception as e:
    print(f"❌ Error loading model: {e}")
    import traceback
    traceback.print_exc()
    model = None
    class_names = None


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def preprocess_image(img_path, img_size=128):
    """Load and preprocess image"""
    try:
        img = cv2.imread(img_path)
        if img is None:
            return None

        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Resize to model input size
        img = cv2.resize(img, (img_size, img_size))

        # Normalize to [0, 1]
        img = img.astype('float32') / 255.0

        # Add batch dimension
        img = np.expand_dims(img, axis=0)

        return img
    except Exception as e:
        print(f"Error preprocessing image: {e}")
        return None


@app.route('/', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'FSL Recognition API is running',
        'model_loaded': model is not None,
        'num_classes': len(class_names) if class_names is not None else 0
    })


@app.route('/predict', methods=['POST'])
def predict():
    """
    Predict sign language from image

    Expected: multipart/form-data with 'image' file
    Returns: JSON with prediction, confidence, and all class probabilities
    """

    # Check if model is loaded
    if model is None or class_names is None:
        return jsonify({'error': 'Model not loaded'}), 500

    # Check if image is in request
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in request'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {ALLOWED_EXTENSIONS}'}), 400

    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Preprocess image
        img = preprocess_image(filepath, IMG_SIZE)

        if img is None:
            return jsonify({'error': 'Could not process image'}), 400

        # Make prediction
        prediction = model.predict(img, verbose=0)
        predicted_class_idx = np.argmax(prediction[0])
        confidence = float(prediction[0][predicted_class_idx])
        predicted_class = str(class_names[predicted_class_idx])

        # Get all class probabilities (top 5)
        top_5_indices = np.argsort(prediction[0])[-5:][::-1]
        top_5_predictions = [
            {
                'class': str(class_names[idx]),
                'confidence': float(prediction[0][idx])
            }
            for idx in top_5_indices
        ]

        # Clean up uploaded file
        os.remove(filepath)

        return jsonify({
            'status': 'success',
            'prediction': predicted_class,
            'confidence': confidence,
            'confidence_percentage': f"{confidence * 100:.2f}%",
            'top_5_predictions': top_5_predictions
        }), 200

    except Exception as e:
        print(f"Error in prediction: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/classes', methods=['GET'])
def get_classes():
    """Get list of all classes"""
    if class_names is None:
        return jsonify({'error': 'Model not loaded'}), 500

    return jsonify({
        'num_classes': len(class_names),
        'classes': list(class_names)
    }), 200


@app.route('/info', methods=['GET'])
def get_info():
    """Get model information"""
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500

    return jsonify({
        'model_type': 'CNN',
        'input_shape': model.input_shape,
        'output_shape': model.output_shape,
        'total_params': int(model.count_params()),
        'image_size': IMG_SIZE,
        'num_classes': len(class_names),
        'classes': list(class_names)
    }), 200


@app.route('/api/fsl/sequence/start', methods=['POST'])
def start_sequence():
    """Start a new learning sequence"""
    data = request.json
    
    # Generate session ID if not provided
    session_id = data.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Create new sequence
    seq = ProgressiveSignSequence()
    
    # Determine signs to learn
    if 'part' in data:
        part_idx = int(data['part'])
        # Map part to signs
        parts_map = {
            1: ['A', 'B', 'C', 'D', 'E'],
            2: ['F', 'G', 'H', 'I', 'J'],
            3: ['K', 'L', 'M', 'N', 'O'],
            4: ['P', 'Q', 'R', 'S', 'T'],
            5: ['U', 'V', 'W', 'X', 'Y', 'Z']
        }
        signs = parts_map.get(part_idx, ['A'])
        seq.set_sequence(signs)
    elif 'signs' in data:
        seq.set_sequence(data['signs'])
    else:
        # Default fallback
        seq.set_sequence(['A', 'B', 'C'])
    
    active_sequences[session_id] = seq
    
    return jsonify({
        'status': 'started',
        'session_id': session_id,
        'target': seq.get_current_target(),
        'sequence': seq.sequence,
        'progress': seq.get_progress()
    })


@app.route('/api/fsl/sequence/check', methods=['POST'])
def check_sequence_sign():
    """Check a sign against the current sequence target"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in active_sequences:
        # If no session, create a temporary one (graceful degradation)
        # But ideally we want persistent state.
        # For now, return error to force restart
        return jsonify({'error': 'Session not found. Please restart part.'}), 404
    
    seq = active_sequences[session_id]
    result = seq.check_sign(data.get('sign'), data.get('confidence', 0.0))
    
    return jsonify(result)


@app.route('/api/fsl/sequence/skip', methods=['POST'])
def skip_sequence_sign():
    """Skip the current sign in the sequence"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in active_sequences:
        return jsonify({'error': 'Session not found'}), 404
    
    seq = active_sequences[session_id]
    result = seq.skip_current()
    
    return jsonify(result)


@app.route('/api/fsl/sequence/progress', methods=['GET'])
def get_sequence_progress():
    """Get current progress for a session"""
    session_id = request.args.get('session_id')
    
    if not session_id or session_id not in active_sequences:
        return jsonify({'error': 'Session not found'}), 404
        
    seq = active_sequences[session_id]
    return jsonify(seq.get_progress())


if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)
