"""
Vercel Serverless Function Entry Point
This file handles routing for Vercel serverless functions using Mangum adapter
"""
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.app.main import app
from mangum import Mangum

# Create Mangum handler for Vercel serverless functions
handler = Mangum(app, lifespan="off")
