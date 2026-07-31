# Re-export the app from run.py for uvicorn compatibility
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import app

__all__ = ['app']
