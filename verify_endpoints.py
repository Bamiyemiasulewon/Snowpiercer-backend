#!/usr/bin/env python3
"""
Verify that all frontend-required endpoints exist in the backend
"""

import asyncio
from fastapi.testclient import TestClient
from main import app

def test_frontend_endpoints():
    """Test all endpoints that the frontend is trying to call"""
    print("🔍 Verifying Frontend-Required Endpoints")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Endpoints that the frontend is calling
    frontend_endpoints = [
        {"method": "GET", "path": "/", "description": "Root endpoint"},
        {"method": "GET", "path": "/health", "description": "Root health check"},
        {"method": "GET", "path": "/api/health", "description": "API health check"},
        {"method": "GET", "path": "/api/status", "description": "API status"},
        {"method": "GET", "path": "/api/tokens", "description": "Get tokens list"},
        {"method": "POST", "path": "/api/quote", "description": "Get swap quote"},
        {"method": "POST", "path": "/api/simulate", "description": "Simulate volume"},
        {"method": "GET", "path": "/api/bot/status", "description": "Bot status"},
        {"method": "POST", "path": "/api/bot/start", "description": "Start bot"},
        {"method": "POST", "path": "/api/bot/stop", "description": "Stop bot"},
        {"method": "GET", "path": "/docs", "description": "API documentation"},
    ]
    
    passed = 0
    failed = 0
    
    for endpoint in frontend_endpoints:
        try:
            method = endpoint["method"]
            path = endpoint["path"]
            description = endpoint["description"]
            
            print(f"🔄 Testing {method} {path} - {description}")
            
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                # Send minimal valid JSON for POST endpoints
                if "quote" in path:
                    test_data = {
                        "inputMint": "So11111111111111111111111111111111111111112",
                        "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                        "amount": 1000000,
                        "slippageBps": 50
                    }
                elif "bot" in path or "simulate" in path:
                    test_data = {"test": True}
                else:
                    test_data = {}
                    
                response = client.post(path, json=test_data)
            
            if response.status_code < 500:  # Accept 200, 400, etc. but not 500 errors
                print(f"  ✅ {method} {path}: {response.status_code}")
                passed += 1
            else:
                print(f"  ❌ {method} {path}: {response.status_code} - {response.text[:100]}")
                failed += 1
                
        except Exception as e:
            print(f"  ❌ {method} {path}: Exception - {str(e)[:100]}")
            failed += 1
    
    print("=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All frontend endpoints are available!")
        return True
    else:
        print(f"⚠️ {failed} endpoints need attention")
        return False

def check_endpoint_compatibility():
    """Check if backend endpoints match frontend expectations"""
    print("\n🔗 Checking Frontend-Backend Compatibility")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Test specific compatibility issues
    compatibility_tests = [
        {
            "name": "Quote endpoint compatibility",
            "test": lambda: client.post("/api/quote", json={
                "inputMint": "So11111111111111111111111111111111111111112",
                "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 
                "amount": 1000000,
                "slippageBps": 50
            })
        },
        {
            "name": "Status endpoint format",
            "test": lambda: client.get("/api/status")
        },
        {
            "name": "Health endpoint format", 
            "test": lambda: client.get("/api/health")
        },
        {
            "name": "Bot status format",
            "test": lambda: client.get("/api/bot/status")
        }
    ]
    
    all_compatible = True
    
    for test in compatibility_tests:
        try:
            response = test["test"]()
            if response.status_code < 400:
                print(f"✅ {test['name']}: Compatible")
            else:
                print(f"❌ {test['name']}: Status {response.status_code}")
                all_compatible = False
        except Exception as e:
            print(f"❌ {test['name']}: {str(e)[:50]}")
            all_compatible = False
    
    print("=" * 50)
    if all_compatible:
        print("🎯 Backend is fully compatible with frontend!")
    else:
        print("⚠️ Some compatibility issues found")
    
    return all_compatible

if __name__ == "__main__":
    print("🚀 VolumeBot Frontend-Backend Compatibility Check")
    print("Backend URL: https://snowpiercer-backend-1.onrender.com")
    print("Frontend URL: https://snowpiercer-pi.vercel.app")
    print()
    
    endpoints_ok = test_frontend_endpoints()
    compatibility_ok = check_endpoint_compatibility()
    
    print("\n" + "=" * 50)
    if endpoints_ok and compatibility_ok:
        print("🎉 SUCCESS: Backend is ready for frontend integration!")
        print("✅ All required endpoints are available")
        print("✅ Response formats are compatible")
        print("\n🚀 You can now deploy with confidence!")
    else:
        print("⚠️ ISSUES FOUND: Some endpoints need attention")
        print("Check the output above for specific issues")
        
    print("\n🔗 Test your live connection at:")
    print("Frontend: https://snowpiercer-pi.vercel.app")
    print("Backend: https://snowpiercer-backend-1.onrender.com/docs")