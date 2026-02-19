import sys
import os
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def log(msg):
    print(msg)
    with open("test_results.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def get_stream_content(response):
    """Helper to consume stream and return full text."""
    content = ""
    for chunk in response.iter_text():
        if chunk:
            content += chunk
    return content

def test_language_lock_python():
    log("\n--- Testing Python Language Lock (Streaming) ---")
    response = client.post("/api/chat", json={
        "message": "Write a function to calculate fibonacci numbers.",
        "language": "Python"
    })
    if response.status_code == 200:
        reply = get_stream_content(response)
        log("Reply received (Streamed).")
        
        if "def " in reply and "public class" not in reply:
             log("✅ Python syntax detected.")
        else:
             log("❌ Python syntax check failed.")
             # log(reply[:500])
             
        # Structure check might be less strict now as we want conciseness, but let's see
        # The prompt still asks for structure.
        if "🧠" in reply or "Problem" in reply: 
             log("✅ Structure check passed (heuristically).")
        else:
             log("⚠️ Structure check warning (might be too concise).")
    else:
        log(f"❌ Request failed with status {response.status_code}")
        # log(response.text)

def test_language_lock_java():
    log("\n--- Testing Java Language Lock (Streaming) ---")
    response = client.post("/api/chat", json={
        "message": "Write a function to calculate fibonacci numbers.",
        "language": "Java"
    })
    if response.status_code == 200:
        reply = get_stream_content(response)
        log("Reply received.")
        if "public class" in reply and "def " not in reply:
             log("✅ Java syntax detected.")
        else:
             log("❌ Java syntax check failed.")
    else:
        log(f"❌ Request failed with status {response.status_code}")

def test_cross_language_enforcement():
    log("\n--- Testing Cross-Language Enforcement (Asking for Python in Java mode) ---")
    response = client.post("/api/chat", json={
        "message": "Write a python script to print hello world",
        "language": "Java"
    })
    
    if response.status_code == 200:
        reply = get_stream_content(response)
        log("Reply received.")
        # The model should REFUSE or Provide Java equivalent.
        if "def " not in reply and ("print(" not in reply or "System.out.println" in reply):
             log("✅ Successfully avoided Python syntax in Java mode.")
        else:
             log("⚠️ Potential leak of Python syntax in Java mode.")
    else:
         log(f"❌ Request failed with status {response.status_code}")
         
def test_context_gating():
    log("\n--- Testing Context Gating (Streaming) ---")
    # 1. General question (should ignore context)
    response = client.post("/api/chat", json={
        "message": "What is the capital of France?",
        "language": "Python",
        "context_code": "def malicious_code(): pass"
    })
    reply = get_stream_content(response)
    if "Paris" in reply and "def " not in reply: # Should be short and simple
        log("✅ Context Gating Passed: Context ignored for general question.")
    else:
        log("⚠️ Context Gating Warning: Context might have been used or answer is weird.")
        
    # 2. Specific question (should use context)
    response = client.post("/api/chat", json={
        "message": "Explain this code",
        "language": "Python",
        "context_code": "def magic_function(): return 42"
    })
    reply = get_stream_content(response)
    if "magic_function" in reply:
        log("✅ Context Gating Passed: Context used when requested.")
    else:
        log("⚠️ Context Gating Warning: Context NOT used when requested.")


if __name__ == "__main__":
    test_language_lock_python()
    test_language_lock_java()
    test_cross_language_enforcement()
    test_context_gating()
