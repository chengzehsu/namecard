#!/usr/bin/env python3
"""
Simple test to verify CI/CD basic functionality
"""

def test_basic_functionality():
    """Test that basic Python functionality works"""
    assert 1 + 1 == 2
    assert "hello" == "hello"
    assert True is True

def test_imports():
    """Test that core modules can be imported"""
    import sys
    import os
    assert sys.version_info >= (3, 8)
    assert os.path.exists('.')

if __name__ == "__main__":
    test_basic_functionality()
    test_imports()
    print("✅ All basic tests passed!")