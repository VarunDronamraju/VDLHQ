import os
import sys
import time
import requests
import jwt
from datetime import datetime, timedelta, timezone

# Ensure we can find the .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Please install python-dotenv: pip install python-dotenv")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000/api/v1"
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret-locationhq-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def create_demo_token(role="ops", client_id=None):
    payload = {
        "sub": "demo_user",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if client_id:
        payload["client_id"] = str(client_id)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def print_step(title):
    print(f"\n{'='*50}\n🚀 STEP: {title}\n{'='*50}")

def print_json(data):
    import json
    print(json.dumps(data, indent=2))

def main():
    print("Starting LocationHQ Demo Flow...")
    
    # 1. Check health
    try:
        health_resp = requests.get("http://127.0.0.1:8000/health")
        if health_resp.status_code != 200:
            print(f"Server is not healthy! Status: {health_resp.status_code}")
            sys.exit(1)
        print("✅ Server is running and healthy!")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running! Please start it with: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    # 2. Create Inquiry (Public Endpoint)
    print_step("1. Creating an Inquiry")
    inquiry_payload = {
        "client": {
            "name": "Demo Studio Productions",
            "email": "demo@example.com",
            "phone": "+1234567890"
        },
        "shoot_type": "commercial",
        "location_requirements": "Looking for a modern, sunlit apartment in a high-rise building with a view of the city skyline."
    }
    
    resp = requests.post(f"{BASE_URL}/inquiry", json=inquiry_payload)
    if resp.status_code != 202:
        print(f"Failed to create inquiry: {resp.text}")
        sys.exit(1)
        
    inquiry_data = resp.json()
    lead_id = inquiry_data.get("lead_id")
    print("✅ Inquiry created successfully!")
    print(f"Lead ID: {lead_id}")
    
    # Wait for background pipeline to process
    print("Waiting 5 seconds for background pipeline (A1, A2, C2, A3) to process the lead...")
    time.sleep(5)
    
    # Generate Ops Token
    ops_token = create_demo_token(role="ops")
    headers = {"Authorization": f"Bearer {ops_token}"}
    
    # 3. Check Pipeline
    print_step("2. Checking Ops Pipeline")
    pipeline_resp = requests.get(f"{BASE_URL}/ops/pipeline", headers=headers)
    
    if pipeline_resp.status_code == 200:
        pipeline_data = pipeline_resp.json()
        print(f"Found {len(pipeline_data)} leads in pipeline.")
        # Find our specific lead
        demo_lead = next((l for l in pipeline_data if l["id"] == lead_id), None)
        if demo_lead:
            print("✅ Our demo lead is in the pipeline!")
            print(f"Current Status: {demo_lead['status']}")
            print(f"Readiness Score: {demo_lead['readiness_score']}")
        else:
            print("⚠️ Demo lead not found in pipeline response.")
    else:
        print(f"Failed to fetch pipeline: {pipeline_resp.text}")

    # 4. Trigger Transition
    print_step("3. Triggering State Transition (Booking the Lead)")
    transition_payload = {
        "new_state": "booked",
        "actor": "demo_ops_user",
        "reason": "Demo workflow transition to booked."
    }
    
    trans_resp = requests.post(f"{BASE_URL}/ops/leads/{lead_id}/action", json=transition_payload, headers=headers)
    if trans_resp.status_code == 200:
        print("✅ Lead successfully transitioned!")
        print_json(trans_resp.json())
    else:
        print(f"Failed to transition lead (it might not be in 'ready' or 'matched' state): {trans_resp.status_code}")
        print(trans_resp.text)
        print("\nNote: The lead might still be processing or waiting for information.")

    # 5. View Analytics
    print_step("4. Viewing Analytics Dashboard")
    analytics_resp = requests.get(f"{BASE_URL}/ops/analytics", headers=headers)
    
    if analytics_resp.status_code == 200:
        print("✅ Analytics successfully fetched!")
        print_json(analytics_resp.json())
    else:
        print(f"Failed to fetch analytics: {analytics_resp.text}")
        
    print("\n" + "="*50)
    print("🎉 Demo complete!")
    print("="*50)

if __name__ == "__main__":
    main()
