from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import sys
import numpy as np
import json
import urllib.request
import io

app = Flask(__name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# Create uploads folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import OCR module (lazy import)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'static'))
ocr = None  # Will be initialized on first use

def convert_numpy_types(obj):
    """
    Convert numpy types and other non-serializable types to native Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, tuple):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    return obj

def get_ocr():
    global ocr
    if ocr is None:
        try:
            from ocr import OCRExtractor
            ocr = OCRExtractor(languages=['en'], gpu=False)
        except Exception as e:
            print(f"Warning: OCR initialization failed: {e}")
            raise
    return ocr

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Home Page
@app.route("/")
def home():
    return render_template("index.html")


# Gamification Page (we will build this next)
@app.route("/gamification")
def gamification():
    return render_template("gamification.html")

#challenges page
@app.route("/challenges")
def challenges():
    return render_template("challenges.html")


# OCR Processing Endpoint
@app.route("/api/ocr", methods=['POST'])
def process_ocr():
    """
    Handle OCR file upload and process the receipt
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use: png, jpg, jpeg, gif, bmp, tiff, webp'}), 400
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process with OCR
        ocr_instance = get_ocr()
        extracted_data = ocr_instance.extract_text_from_image(filepath)
        
        if extracted_data is None:
            return jsonify({'error': 'Failed to process image'}), 500
        
        # Convert numpy types to native Python types for JSON serialization
        serializable_data = convert_numpy_types(extracted_data)
        
        return jsonify({
            'success': True,
            'extracted_text': serializable_data['full_text'],
            'detailed_data': serializable_data['detailed_data'],
            'total_detections': serializable_data['total_detections'],
            'filename': filename
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# DroidCam Image Proxy Endpoint
@app.route("/api/droidcam", methods=['GET'])
def get_droidcam_image():
    """
    Fetch image from DroidCam and return it
    This bypasses CORS restrictions
    """
    try:
        ip = request.args.get('ip')
        port = request.args.get('port', '4747')
        
        if not ip:
            return jsonify({'error': 'IP address required'}), 400
        
        # Try with /video endpoint first, then try direct MJPEG stream
        droidcam_urls = [
            f"http://{ip}:{port}/video",  # Standard DroidCam endpoint
            f"http://{ip}:{port}/mjpegfeed",  # Alternative MJPEG endpoint
            f"http://{ip}:{port}",  # Root endpoint
        ]
        
        image_data = None
        last_error = None
        
        for droidcam_url in droidcam_urls:
            try:
                # Prepare request with proper headers
                req = urllib.request.Request(
                    droidcam_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Connection': 'keep-alive',
                        'Accept': 'image/jpeg, image/png, image/*'
                    }
                )
                
                # Add timeout of 10 seconds
                response = urllib.request.urlopen(req, timeout=10)
                image_data = response.read()
                
                if image_data and len(image_data) > 100:  # Ensure we got actual image data
                    print(f"✓ Successfully connected to DroidCam at {droidcam_url}")
                    break
                    
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
                last_error = str(e)
                print(f"✗ Failed to connect to {droidcam_url}: {e}")
                continue
        
        if not image_data:
            error_msg = f"DroidCam connection failed. Tried multiple endpoints. Last error: {last_error}"
            print(f"Error: {error_msg}")
            return jsonify({'error': error_msg}), 503
        
        # Return image with proper content type
        return send_file(
            io.BytesIO(image_data),
            mimetype='image/jpeg',
            as_attachment=False
        )
        
    except Exception as e:
        error_msg = f'Failed to fetch DroidCam image: {str(e)}'
        print(f"Error: {error_msg}")
        return jsonify({'error': error_msg}), 500


# DroidCam Connectivity Test Endpoint
@app.route("/api/droidcam-test", methods=['GET'])
def test_droidcam_connection():
    """
    Test connectivity to DroidCam without returning image.
    Helps diagnose connection issues.
    
    NOTE: If running in a dev container (Docker, Codespaces, etc), the container
    may not have direct network access to your local phone/LAN. In that case:
    - Run this Flask app on your host machine instead
    - Or configure the container with host networking (--network=host)
    - The frontend will suggest this in the error message
    """
    try:
        ip = request.args.get('ip')
        port = request.args.get('port', '4747')
        
        if not ip:
            return jsonify({'error': 'IP address required', 'status': 'failed'}), 400
        
        # Try to connect to DroidCam
        test_urls = [
            f"http://{ip}:{port}/video",
            f"http://{ip}:{port}/mjpegfeed",
            f"http://{ip}:{port}",
        ]
        
        results = {}
        for test_url in test_urls:
            try:
                req = urllib.request.Request(
                    test_url,
                    headers={'User-Agent': 'Mozilla/5.0', 'Connection': 'keep-alive'}
                )
                response = urllib.request.urlopen(req, timeout=3)
                results[test_url] = 'SUCCESS'
                return jsonify({
                    'status': 'success',
                    'message': f'Connection successful to {test_url}',
                    'ip': ip,
                    'port': port
                }), 200
            except Exception as e:
                results[test_url] = str(e)
        
        # All attempts failed
        return jsonify({
            'status': 'failed',
            'ip': ip,
            'port': port,
            'message': 'Could not connect to DroidCam. Tried all endpoints.',
            'attempts': results
        }), 503
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'failed'}), 500


if __name__ == "__main__":
    app.run(debug=True)