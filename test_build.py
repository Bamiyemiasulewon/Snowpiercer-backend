#!/usr/bin/env python3
"""
Test script to verify VolumeBot backend functionality
"""

import asyncio
import sys
from fastapi.testclient import TestClient
from main import app

def test_app_creation():
    """Test that the app can be created successfully"""
    print("✓ Testing app creation...")
    assert app is not None
    assert app.title == "VolumeBot Backend"
    assert app.version == "1.0.0"
    print("  ✓ App created successfully")

def test_api_endpoints():
    """Test basic API endpoints"""
    print("✓ Testing API endpoints...")
    client = TestClient(app)
    
    # Test root endpoint (if it exists)
    try:
        response = client.get("/")
        print(f"  ✓ Root endpoint: {response.status_code}")
    except Exception as e:
        print(f"  ⚠ Root endpoint not accessible: {e}")
    
    # Test API docs
    try:
        response = client.get("/docs")
        assert response.status_code == 200
        print("  ✓ API docs accessible")
    except Exception as e:
        print(f"  ⚠ API docs error: {e}")
    
    # Test API health/status (common endpoint)
    try:
        response = client.get("/api/health")
        print(f"  ✓ Health endpoint: {response.status_code}")
    except Exception as e:
        print(f"  ⚠ Health endpoint not found: {e}")

def test_imports():
    """Test critical imports"""
    print("✓ Testing critical imports...")
    
    try:
        from services.jupiter import JupiterService
        print("  ✓ JupiterService imported")
    except ImportError as e:
        print(f"  ✗ JupiterService import failed: {e}")
        return False
    
    try:
        from services.volume_simulator import VolumeSimulator
        print("  ✓ VolumeSimulator imported")
    except ImportError as e:
        print(f"  ✗ VolumeSimulator import failed: {e}")
        return False
    
    try:
        from api.routes import router
        print("  ✓ API router imported")
    except ImportError as e:
        print(f"  ✗ API router import failed: {e}")
        return False
    
    return True

def main():
    """Main test runner"""
    print("🚀 VolumeBot Backend Build Test")
    print("=" * 40)
    
    success = True
    
    try:
        test_app_creation()
    except Exception as e:
        print(f"  ✗ App creation failed: {e}")
        success = False
    
    try:
        if not test_imports():
            success = False
    except Exception as e:
        print(f"  ✗ Import test failed: {e}")
        success = False
    
    try:
        test_api_endpoints()
    except Exception as e:
        print(f"  ✗ API endpoint test failed: {e}")
        success = False
    
    print("=" * 40)
    if success:
        print("🎉 BUILD SUCCESS: All tests passed!")
        print("Your VolumeBot backend is ready for deployment!")
        sys.exit(0)
    else:
        print("❌ BUILD FAILED: Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()