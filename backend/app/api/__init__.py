# app/api/__init__.py
from flask import Flask
from app.api.routes import api_routes

def create_app():
    app = Flask(__name__)
    
    # Register the API routes blueprint
    app.register_blueprint(api_routes)
    
    return app
