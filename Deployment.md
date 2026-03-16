# Deployment Guide for Filipino Sign Language Learning System

This guide provides step-by-step instructions for deploying the Filipino Sign Language (FSL) Learning Web Application on Hugging Face, including model hosting, web application deployment, database setup, and data collection processes.

## Table of Contents
1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Data Collection](#data-collection)
4. [Model Preparation and Deployment](#model-preparation-and-deployment)
5. [Database Setup](#database-setup)
6. [Web Application Deployment](#web-application-deployment)
7. [Complete Deployment Steps](#complete-deployment-steps)
8. [Troubleshooting](#troubleshooting)

## System Overview

The FSL Learning System consists of:
- **Machine Learning Model**: TensorFlow/Keras model for sign language recognition
- **Web Application**: Flask-based web app with user authentication and gamification
- **Database**: SQLAlchemy with SQLite for user data and progress tracking
- **Data Collection Tools**: Scripts for collecting hand landmark data for model training

## Prerequisites

- Hugging Face account
- Python 3.8+
- Git
- Webcam (for data collection)
- MediaPipe, TensorFlow, Flask, and other dependencies listed in `requirements.txt`

## Data Collection

### Training Data Collection

The system uses hand landmarks extracted via MediaPipe for sign recognition. To collect training data:

1. **Setup Environment**:
   ```bash
   cd "Sign Language model"
   pip install -r requirements.txt
   ```

2. **Run Data Collector**:
   ```bash
   python dataset_collector.py
   ```

3. **Collection Process**:
   - Press a letter key (A-Z) to start collecting for that sign
   - Position your hand to form the sign
   - Press SPACE to capture and save the landmark data
   - Press DELETE to remove the last captured frame
   - Press Q to quit

4. **Data Structure**:
   - Data is saved as CSV files in `datasets/FSL_Landmarks/`
   - Each file contains 21 hand landmarks × 3 coordinates (x, y, z)
   - Target: 350-400 samples per letter

5. **Additional Signs**:
   - The system supports Filipino-specific signs (e.g., LALAMUNAN, MAHIRAP, etc.)
   - Follow the same process for custom signs

### User Data Collection

The application collects user progress and feedback data as outlined in `DATA_COLLECTION.md`:
- User accounts (email, hashed password, progress)
- Session data (performance metrics, timestamps)
- Sign attempts (AI predictions, confidence scores)
- Gamification data (EXP, levels)

## Model Preparation and Deployment

### 1. Train the Model

```bash
cd "Sign Language model"
python train_model.py
```

This creates:
- `models/fsl_model.h5` (trained model)
- `models/fsl_model_classes.npy` (class labels)
- `models/fsl_model_metadata.npy` (model metadata)

### 2. Upload Model to Hugging Face

1. Go to [Hugging Face Models](https://huggingface.co/models)
2. Click "New Model"
3. Set model type to "TensorFlow"
4. Upload the following files:
   - `fsl_model.h5`
   - `fsl_model_classes.npy`
   - `fsl_model_metadata.npy`
   - `landmark_scaler_mean.npy`
   - `landmark_scaler_scale.npy`

5. Add model card with description and usage instructions

### 3. Create Model Inference API

Use the `fsl_inference.py` module for predictions. The model can be loaded and used for real-time inference.

## Database Setup

### Limitations on Hugging Face

Hugging Face Spaces are stateless and don't support persistent SQLite databases. For production deployment, consider:

### Option 1: External Database (Recommended)

1. **Use a cloud database service**:
   - PostgreSQL on Railway, Render, or Supabase
   - MongoDB Atlas
   - AWS RDS

2. **Update configuration**:
   - Modify `website/__init__.py` to use external database URL
   - Set environment variable: `DATABASE_URL=postgresql://user:pass@host:port/db`

### Option 2: File-based Storage (Development Only)

For demo purposes, use SQLite with file storage, but note that data will reset on Space restarts.

## Web Application Deployment

### Option 1: Hugging Face Spaces (Recommended)

1. **Create a new Space**:
   - Go to [Hugging Face Spaces](https://huggingface.co/spaces)
   - Choose "Gradio" or "Streamlit" template
   - Set to public or private

2. **Adapt the Flask App**:
   Since Spaces work best with Gradio/Streamlit, create a `app.py` with Gradio interface:

   ```python
   import gradio as gr
   from fsl_inference import get_inference_engine
   # ... implement Gradio interface for sign recognition
   ```

3. **Upload Files**:
   - `app.py` (Gradio interface)
   - Model files
   - `requirements.txt`
   - Static files and templates

4. **Configure Space**:
   - Set Python version to 3.8+
   - Add required packages in requirements.txt
   - Set startup command

### Option 2: Alternative Deployment

For full Flask functionality, consider:
- **Railway**: Supports Flask with persistent databases
- **Render**: Free tier available
- **Heroku**: Traditional Flask deployment

## Complete Deployment Steps

1. **Collect and Prepare Data**:
   ```bash
   # Collect training data
   cd "Sign Language model"
   python dataset_collector.py
   
   # Train model
   python train_model.py
   ```

2. **Setup Database**:
   - Choose external database provider
   - Update database configuration in code

3. **Upload Model to Hugging Face**:
   - Create model repository
   - Upload model files and metadata

4. **Create Hugging Face Space**:
   - Create new Space with Gradio
   - Implement web interface
   - Upload application code

5. **Configure Environment**:
   - Set environment variables for database and model paths
   - Test the deployment

6. **Deploy and Test**:
   - Push code to Space
   - Test sign recognition functionality
   - Verify user registration and progress tracking

## Troubleshooting

### Common Issues

1. **Model Loading Errors**:
   - Ensure all model files are uploaded
   - Check file paths in code
   - Verify TensorFlow version compatibility

2. **Database Connection**:
   - Confirm database URL is correct
   - Check firewall settings for external databases
   - Ensure proper SSL configuration

3. **Webcam Access**:
   - Spaces may have limitations with webcam access
   - Consider using uploaded images for demos

4. **Memory Issues**:
   - Optimize model size if Space runs out of memory
   - Use model quantization if needed

### Performance Optimization

- Use model quantization for smaller file sizes
- Implement caching for frequently accessed data
- Optimize database queries
- Use CDN for static assets

## Support

For issues with deployment or data collection:
- Check Hugging Face documentation
- Review application logs in Space settings
- Test locally before deploying

## License

This deployment guide is part of the FSL Learning System. Ensure compliance with all applicable licenses and data privacy regulations when collecting and storing user data.