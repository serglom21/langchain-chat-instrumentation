#!/usr/bin/env python3
"""
Test script for hybrid instrumentation web server.

This script tests:
1. Span ingestion (OTel traces)
2. Error capturing (Sentry Issues)
3. Linking between traces and errors
"""

import requests
import time
import json


BASE_URL = "http://localhost:8003"


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_health():
    """Test health endpoint."""
    print_section("Test 1: Health Check")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Health check passed")
    else:
        print("❌ Health check failed")
    
    return response.status_code == 200


def test_successful_chat():
    """Test normal chat - creates trace without errors."""
    print_section("Test 2: Successful Chat (Trace Only)")
    
    payload = {
        "message": "Hello, how are you?",
        "session_id": "test-session-1"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Chat successful")
        print("📊 Check Sentry Performance tab for the trace")
        print("   You should see spans for:")
        print("   - POST /api/chat")
        print("   - Process Chat Workflow")
        print("   - Input Validation")
        print("   - LLM Processing")
        print("   - Response Formatting")
        print("   - Individual node operations")
    else:
        print("\n❌ Chat failed")
    
    return response.status_code == 200


def test_chat_with_validation_error():
    """Test chat with error in validation span (realistic scenario)."""
    print_section("Test 3: Chat with Validation Error in Span")
    
    payload = {
        "message": "Hello, this is a test message",
        "session_id": "test-session-validation",
        "inject_error": "validation"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    print("This will inject an error in the 'Input Validation' span")
    print("but the request will still succeed (error is recovered)")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload
    )
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Chat succeeded despite validation error!")
        print("\n🔍 Now check Sentry:")
        print("\n📊 Performance Tab:")
        print("   - Find the trace for POST /api/chat")
        print("   - See full workflow with all spans:")
        print("     • POST /api/chat (parent)")
        print("     • Process Chat Workflow")
        print("       • Input Validation ⚠️ (has error)")
        print("       • LLM Processing")
        print("       • Response Formatting")
        print("\n🐛 Issues Tab:")
        print("   - Find: 'ValueError: TEST ERROR: Validation failed'")
        print("   - Click it → see full stack trace")
        print("   - Look for tag: 'span: validation'")
        print("   - Click 'otel.trace_id' tag")
        print("   - Should jump to the EXACT span in the trace!")
        print("\n💡 This shows realistic error handling:")
        print("   - Error occurs in specific span")
        print("   - Error captured and sent to Sentry")
        print("   - Workflow recovers and continues")
        print("   - Overall request succeeds")
        print("   - Error is linked to exact span in trace!")
    else:
        print("\n❌ Test failed")
    
    return response.status_code == 200


def test_chat_with_llm_error():
    """Test chat with error in LLM span (realistic scenario)."""
    print_section("Test 4: Chat with LLM Error in Span")
    
    payload = {
        "message": "What is the meaning of life?",
        "session_id": "test-session-llm",
        "inject_error": "llm"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    print("This will inject a timeout error in the 'LLM Processing' span")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload
    )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        print("\n✅ Request completed (error recovered)")
        print("🔍 Check Sentry Issues for: 'TimeoutError: TEST ERROR: OpenAI API timeout'")
        print("   Tag 'span: llm' should help identify where it occurred")
        print("   The error is linked to the 'LLM Processing' span in the trace")
    
    return response.status_code == 200


def test_chat_with_formatting_error():
    """Test chat with error in formatting span (realistic scenario)."""
    print_section("Test 5: Chat with Formatting Error in Span")
    
    payload = {
        "message": "Tell me a joke",
        "session_id": "test-session-format",
        "inject_error": "formatting"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    print("This will inject an error in the 'Response Formatting' span")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload
    )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        print("\n✅ Request completed (error recovered)")
        print("🔍 Check Sentry Issues for: 'RuntimeError: TEST ERROR: Failed to format response'")
        print("   Tag 'span: formatting' shows where it occurred")
        print("   The error is linked to the 'Response Formatting' span")
    
    return response.status_code == 200


def test_standalone_validation_error():
    """Test validation error - creates trace + error in Issues."""
    print_section("Test 6: Standalone Validation Error (Trace + Issue)")
    
    payload = {
        "error_type": "validation"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/test-error",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Error captured successfully!")
        print("\n🔍 Now check Sentry:")
        print("\n1️⃣  Issues Tab:")
        print("   - Look for: 'ValueError: Invalid input: test validation error'")
        print("   - Click on it to see full stack trace")
        print("   - Look for tags: otel.trace_id, otel.span_id")
        print("\n2️⃣  Performance Tab:")
        print("   - Look for: POST /api/test-error trace")
        print("   - See the span marked as ERROR")
        print("   - See 'Intentional Error Generation' child span")
        print("\n3️⃣  Link between them:")
        print("   - In Issues tab, click the 'otel.trace_id' tag")
        print("   - Should jump to the Performance tab showing the full trace!")
    else:
        print("\n❌ Test failed")
    
    return response.status_code == 200


def test_llm_timeout_error():
    """Test LLM timeout error."""
    print_section("Test 4: LLM Timeout Error (Trace + Issue)")
    
    payload = {
        "error_type": "llm_timeout"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/test-error",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("\n✅ LLM timeout error captured!")
        print("🔍 Check Sentry Issues for: 'TimeoutError: LLM API timeout'")
    
    return response.status_code == 200


def test_division_error():
    """Test division by zero error."""
    print_section("Test 5: Division Error (Trace + Issue)")
    
    payload = {
        "error_type": "division"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/test-error",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("\n✅ Division error captured!")
        print("🔍 Check Sentry Issues for: 'ZeroDivisionError'")
    
    return response.status_code == 200


def test_empty_chat_message():
    """Test empty message (validation error in chat endpoint)."""
    print_section("Test 6: Empty Message (Should Not Create Error)")
    
    payload = {
        "message": "",
        "session_id": "test-session-2"
    }
    
    print(f"Sending: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 400:
        print("\n✅ Validation worked (no error captured)")
        print("📊 Trace created but no Issue (expected behavior)")
    
    return response.status_code == 400


def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪"*35)
    print("  Hybrid Instrumentation Test Suite")
    print("🧪"*35)
    
    print("\nMake sure:")
    print("  1. Server is running: python hybrid_web_main.py")
    print("  2. Environment variables are set (SENTRY_DSN, etc.)")
    print("  3. Sentry dashboard is open in your browser")
    
    input("\nPress Enter to start tests...")
    
    results = {}
    
    try:
        results['health'] = test_health()
        time.sleep(1)
        
        results['successful_chat'] = test_successful_chat()
        time.sleep(2)
        
        # Realistic error scenarios - errors in specific spans
        results['chat_validation_error'] = test_chat_with_validation_error()
        time.sleep(2)
        
        results['chat_llm_error'] = test_chat_with_llm_error()
        time.sleep(2)
        
        results['chat_formatting_error'] = test_chat_with_formatting_error()
        time.sleep(2)
        
        # Standalone test errors
        results['standalone_validation'] = test_standalone_validation_error()
        time.sleep(1)
        
        results['llm_timeout'] = test_llm_timeout_error()
        time.sleep(1)
        
        results['division_error'] = test_division_error()
        time.sleep(1)
        
        results['empty_message'] = test_empty_chat_message()
        
    except requests.exceptions.ConnectionError:
        print("\n\n❌ ERROR: Could not connect to server")
        print("   Make sure the server is running:")
        print("   python hybrid_web_main.py")
        return
    
    # Summary
    print_section("Test Summary")
    
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\nPassed: {passed_count}/{total_count}")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print("\n1. Go to Sentry Dashboard")
    print("\n2. Check Issues Tab:")
    print("   You should see 6 errors:")
    print("   Realistic chat errors (in specific spans):")
    print("   - ValueError (validation span)")
    print("   - TimeoutError (LLM span)")
    print("   - RuntimeError (formatting span)")
    print("   Standalone test errors:")
    print("   - ValueError (standalone)")
    print("   - TimeoutError (standalone)")
    print("   - ZeroDivisionError (standalone)")
    
    print("\n3. Check each error:")
    print("   - Full stack trace ✅")
    print("   - Tags: otel.trace_id, otel.span_id ✅")
    print("   - Tag 'span' shows which span it occurred in ✅")
    print("   - Context: endpoint, error_type ✅")
    
    print("\n4. Check Performance Tab:")
    print("   You should see traces for all requests")
    print("   Some spans will be marked as ERROR")
    
    print("\n5. Test the linking (MOST IMPORTANT):")
    print("   - Open the 'ValueError: TEST ERROR: Validation failed' error")
    print("   - Look for tag 'span: validation'")
    print("   - Click the 'otel.trace_id' tag")
    print("   - Should jump to the Performance tab!")
    print("   - You'll see the FULL trace with:")
    print("     • POST /api/chat")
    print("     • Process Chat Workflow")
    print("       • Input Validation ← ERROR OCCURRED HERE")
    print("       • LLM Processing")
    print("       • Response Formatting")
    print("   - This shows EXACT span where error occurred!")
    
    print("\n6. Realistic scenario benefits:")
    print("   ✅ Errors attached to specific spans in workflow")
    print("   ✅ Overall request can succeed (error recovered)")
    print("   ✅ Full trace shows context before/after error")
    print("   ✅ Can see which step in workflow failed")
    print("   ✅ Can see timing of each step")
    
    print("\n7. Compare to pure OTel:")
    print("   ❌ Pure OTel: errors dropped, no Issues created")
    print("   ✅ Hybrid: rich error details + linked to exact span!")
    
    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    run_all_tests()

