"""
SageMaker Flask Predictor for Wan2.1 - Fixed Version
"""
import os
import json
import logging
import traceback
from flask import Flask, request, jsonify
import signal
import sys

from model_handler import model_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Global variables
model_loaded = False

def load_model():
    """Load the model on startup"""
    global model_loaded
    try:
        logger.info("Starting model loading...")
        success = model_handler.load_model()
        if success:
            model_loaded = True
            logger.info("Model loaded successfully")
        else:
            logger.error("Failed to load model")
            model_loaded = False
    except Exception as e:
        logger.error(f"Exception during model loading: {e}")
        logger.error(traceback.format_exc())
        model_loaded = False

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint required by SageMaker"""
    try:
        if not model_loaded:
            logger.warning("Model not loaded for ping request")
            return jsonify({"status": "unhealthy", "message": "Model not loaded"}), 503
        
        # Perform health check
        health_ok = model_handler.health_check()
        
        if health_ok:
            return jsonify({"status": "healthy"}), 200
        else:
            return jsonify({"status": "unhealthy", "message": "Model health check failed"}), 503
            
    except Exception as e:
        logger.error(f"Ping endpoint error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/invocations', methods=['POST'])
def invocations():
    """Inference endpoint required by SageMaker"""
    try:
        if not model_loaded:
            return jsonify({"error": "Model not loaded"}), 503
        
        # Get request data
        content_type = request.content_type
        
        if content_type == 'application/json':
            input_data = request.get_json()
        else:
            # Try to parse as JSON anyway
            try:
                input_data = json.loads(request.data.decode('utf-8'))
            except:
                return jsonify({"error": "Invalid input format. Expected JSON."}), 400
        
        if not input_data:
            return jsonify({"error": "No input data provided"}), 400
        
        logger.info(f"Received inference request: {json.dumps(input_data, indent=2)[:200]}...")
        
        # Validate required fields
        if 'prompt' not in input_data:
            return jsonify({"error": "Missing required field: prompt"}), 400
        
        # Perform inference
        result = model_handler.predict(input_data)
        
        if result.get("status") == "error":
            logger.error(f"Prediction error: {result.get('error')}")
            return jsonify(result), 500
        
        logger.info("Inference completed successfully")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Invocations endpoint error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health():
    """Additional health endpoint"""
    return ping()

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    # Load model on startup
    load_model()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
else:
    # Load model when imported by gunicorn
    load_model()
