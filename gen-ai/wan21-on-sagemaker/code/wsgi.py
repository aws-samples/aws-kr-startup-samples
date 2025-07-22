"""
WSGI entry point for Gunicorn
"""
import predictor as myapp

# This is just a simple wrapper for gunicorn to find your app.
app = myapp.app
