#!/usr/bin/env python3
"""
Debug version of main.py to diagnose import issues
"""

import os
import sys
import traceback

def debug_environment():
    """Debug the current environment"""
    print("=== ENVIRONMENT DEBUG INFO ===")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"__file__: {__file__}")
    print(f"Directory of __file__: {os.path.dirname(__file__)}")
    print(f"Absolute directory: {os.path.abspath(os.path.dirname(__file__))}")
    
    # Check if directories exist
    root_dir = os.path.abspath(os.path.dirname(__file__))
    src_dir = os.path.join(root_dir, 'src')
    print(f"Root dir exists: {os.path.exists(root_dir)} -> {root_dir}")
    print(f"Src dir exists: {os.path.exists(src_dir)} -> {src_dir}")
    
    # List contents
    if os.path.exists(root_dir):
        print(f"Root dir contents: {os.listdir(root_dir)}")
    if os.path.exists(src_dir):
        print(f"Src dir contents: {os.listdir(src_dir)}")
    
    # Check Python path
    print("Python path:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    
    # Check environment variables
    print("\nEnvironment variables:")
    important_vars = [
        'GOOGLE_API_KEY', 'NOTION_API_KEY', 'NOTION_DATABASE_ID', 
        'TELEGRAM_BOT_TOKEN', 'PORT', 'PYTHONPATH'
    ]
    for var in important_vars:
        value = os.getenv(var, 'NOT SET')
        if value != 'NOT SET' and len(value) > 10:
            value = value[:6] + '...'
        print(f"  {var}: {value}")

def main():
    """Main function with detailed debugging"""
    debug_environment()
    
    # Add paths
    root_dir = os.path.abspath(os.path.dirname(__file__))
    src_dir = os.path.join(root_dir, 'src')
    sys.path.insert(0, root_dir)
    sys.path.insert(0, src_dir)
    
    print("\n=== STARTING IMPORT TESTS ===")
    
    # Test basic config import
    try:
        print("Testing simple_config import...")
        from simple_config import Config
        print("✅ simple_config imported successfully")
        
        # Test config validation
        print("Testing config validation...")
        is_valid = Config.validate()
        print(f"✅ Config validation result: {is_valid}")
        
    except Exception as e:
        print(f"❌ simple_config import failed: {e}")
        traceback.print_exc()
        return 1
    
    # Test main app import
    try:
        print("Testing telegram bot main import...")
        from src.namecard.api.telegram_bot.main import flask_app as app
        print("✅ Telegram Bot main imported successfully")
        
        print("Testing line bot main import...")
        from src.namecard.api.line_bot.main import app as line_app
        print("✅ LINE Bot main imported successfully")
        
    except Exception as e:
        print(f"❌ Main app import failed: {e}")
        traceback.print_exc()
        return 1
    
    # If we get here, try to start the app
    try:
        print("\n=== STARTING FLASK APP ===")
        port = int(os.environ.get('PORT', 5003))
        print(f"Starting Flask app on port {port}...")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False
        )
        
    except Exception as e:
        print(f"❌ Flask app startup failed: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())