#!/usr/bin/env python3
"""
FSL System Verification Script
Tests all components to ensure everything is working correctly
"""

import os
import sys
import importlib

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    pkg = package_name or module_name
    try:
        importlib.import_module(module_name)
        print(f"  ✅ {pkg}")
        return True
    except ImportError as e:
        print(f"  ❌ {pkg}: {e}")
        return False

def check_file(path, description=""):
    """Check if a file exists"""
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✅ {description or path} ({size} bytes)")
        return True
    else:
        print(f"  ❌ {description or path}: NOT FOUND")
        return False

def check_directory(path, description=""):
    """Check if a directory exists"""
    if os.path.isdir(path):
        files = len(os.listdir(path))
        print(f"  ✅ {description or path} ({files} items)")
        return True
    else:
        print(f"  ❌ {description or path}: NOT FOUND")
        return False

def main():
    print("\n" + "🤖 "*20)
    print("\n  FILIP INO SIGN LANGUAGE (FSL) SYSTEM VERIFICATION\n")
    print("🤖 "*20)

    results = {
        "imports": [],
        "files": [],
        "directories": [],
        "summary": {}
    }

    # ========== CHECK DEPENDENCIES ==========
    print_header("1. Checking Python Dependencies")
    
    deps = [
        ("tensorflow", "TensorFlow/Keras"),
        ("mediapipe", "MediaPipe"),
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("sklearn", "scikit-learn"),
        ("pickle", "Pickle"),
        ("csv", "CSV"),
    ]
    
    for module, name in deps:
        results["imports"].append(check_import(module, name))
    
    print(f"\n  Dependencies: {sum(results['imports'])}/{len(results['imports'])} ✓")

    # ========== CHECK PYTHON SCRIPTS ==========
    print_header("2. Checking Python Scripts")
    
    scripts = [
        ("Sign Language model/dataset_collector.py", "Dataset Collector"),
        ("Sign Language model/train_model.py", "Model Trainer"),
        ("Sign Language model/realtime_predict.py", "Real-Time Predictor"),
        ("Sign Language model/fsl_inference.py", "FSL Inference Engine"),
        ("website/views.py", "Flask Views (FSL endpoints)"),
    ]
    
    for path, desc in scripts:
        results["files"].append(check_file(path, desc))
    
    print(f"\n  Python Scripts: {sum(results['files'])}/{len(results['files'])} ✓")

    # ========== CHECK WEB FILES ==========
    print_header("3. Checking Web Components")
    
    web_files = [
        ("website/static/fsl_module.js", "FSL JavaScript Module"),
        ("website/templates/coursealphabets.html", "Alphabet Course Page"),
        ("website/templates/base.html", "Base Template"),
    ]
    
    web_results = []
    for path, desc in web_files:
        web_results.append(check_file(path, desc))
    
    print(f"\n  Web Files: {sum(web_results)}/{len(web_results)} ✓")

    # ========== CHECK DIRECTORIES ==========
    print_header("4. Checking Directories")
    
    dirs_to_check = [
        ("Sign Language model/models", "Models Directory"),
        ("Sign Language model/datasets", "Datasets Directory"),
        ("Sign Language model/datasets/FSL_Landmarks", "FSL Landmarks Dataset"),
        ("website/static", "Static Files"),
        ("website/templates", "Templates"),
    ]
    
    dir_results = []
    for path, desc in dirs_to_check:
        dir_results.append(check_directory(path, desc))
    
    print(f"\n  Directories: {sum(dir_results)}/{len(dir_results)} ✓")

    # ========== CHECK TRAINED MODEL ==========
    print_header("5. Checking Trained Model")
    
    model_files = [
        ("Sign Language model/models/fsl_model.h5", "Trained Model (Keras)"),
        ("Sign Language model/models/fsl_model_classes.npy", "Class Names"),
        ("Sign Language model/models/landmark_scaler.pkl", "Data Scaler"),
    ]
    
    model_results = []
    for path, desc in model_files:
        model_results.append(check_file(path, desc))
    
    has_model = any(model_results)
    print(f"\n  Model Files: {sum(model_results)}/{len(model_results)}")
    
    if not has_model:
        print("\n  ⚠️  No trained model found!")
        print("     Run: python Sign_Language_model/train_model.py")
    else:
        print("  ✅ Model is trained and ready!")

    # ========== CHECK TRAINING DATA ==========
    print_header("6. Checking Training Data")
    
    dataset_dir = "Sign Language model/datasets/FSL_Landmarks"
    if os.path.isdir(dataset_dir):
        csv_files = [f for f in os.listdir(dataset_dir) if f.endswith('.csv')]
        print(f"  CSV Files: {len(csv_files)}")
        if csv_files:
            for csv_file in sorted(csv_files)[:5]:
                path = os.path.join(dataset_dir, csv_file)
                size = os.path.getsize(path)
                lines = sum(1 for line in open(path)) - 1  # -1 for header
                print(f"    ✅ {csv_file}: {lines} samples")
            if len(csv_files) > 5:
                print(f"    ... and {len(csv_files) - 5} more files")
        else:
            print("  ⚠️  No CSV files found!")
            print("     Run: python Sign_Language_model/dataset_collector.py")
    else:
        print(f"  ❌ Dataset directory not found: {dataset_dir}")

    # ========== CHECK DOCUMENTATION ==========
    print_header("7. Checking Documentation")
    
    docs = [
        ("Sign Language model/FSL_SYSTEM_GUIDE.md", "FSL System Guide"),
        ("QUICK_START.md", "Quick Start Guide"),
        ("README_FSL.md", "FSL README"),
        ("Sign Language model/requirements.txt", "Requirements"),
    ]
    
    doc_results = []
    for path, desc in docs:
        doc_results.append(check_file(path, desc))
    
    print(f"\n  Documentation: {sum(doc_results)}/{len(doc_results)} ✓")

    # ========== FINAL SUMMARY ==========
    print_header("8. System Status Summary")
    
    all_imports = sum(results["imports"])
    all_files = sum(results["files"]) + sum(web_results) + sum(model_results) + sum(doc_results)
    all_dirs = sum(dir_results)
    
    total_checks = len(results["imports"]) + len(results["files"]) + len(web_results) + len(model_results) + len(doc_results) + len(dir_results)
    total_passed = all_imports + all_files + all_dirs
    
    print(f"\n  Total Checks: {total_passed}/{total_checks}")
    print(f"\n  Status Components:")
    print(f"    ✅ Dependencies: {all_imports}/{len(results['imports'])}")
    print(f"    ✅ Python Scripts: {sum(results['files'])}/{len(results['files'])}")
    print(f"    ✅ Web Components: {sum(web_results)}/{len(web_results)}")
    print(f"    ✅ Directories: {sum(dir_results)}/{len(dir_results)}")
    print(f"    ✅ Documentation: {sum(doc_results)}/{len(doc_results)}")
    
    if has_model:
        print(f"    ✅ Model: Trained & Ready")
    else:
        print(f"    ⚠️  Model: Not yet trained")
    
    # ========== RECOMMENDATIONS ==========
    print_header("Next Steps")
    
    if total_passed == total_checks and has_model:
        print("\n  🎉 SYSTEM IS FULLY READY!\n")
        print("  You can now:")
        print("    1. Run the website: python main.py")
        print("    2. Visit: http://localhost:5000/coursealphabets")
        print("    3. Try real-time recognition!")
    else:
        print("\n  ⚠️  SETUP INCOMPLETE\n")
        
        if not all_imports == len(results["imports"]):
            print("  1. Install missing dependencies:")
            print("     cd \"Sign Language model\"")
            print("     pip install -r requirements.txt")
        
        if not has_model:
            print("\n  2. Train the model:")
            print("     python Sign_Language_model/train_model.py")
        
        if sum(model_results) < len(model_results):
            print("\n  3. Collect training data first:")
            print("     python Sign_Language_model/dataset_collector.py")
        
        print("\n  For detailed setup, see: QUICK_START.md")

    print("\n" + "="*60)
    print("  Verification Complete!")
    print("="*60 + "\n")

    return total_passed == total_checks

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
