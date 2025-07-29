"""
WSGI entry point for SageMaker inference
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

try:
    from serve import app
    print("Flask app imported successfully from serve.py")
    print("WSGI app ready - model will be initialized on first request")

except ImportError as e:
    print(f"Error importing from serve.py: {e}")
    sys.exit(1)

if __name__ == "__main__":
    app.run(debug=False)