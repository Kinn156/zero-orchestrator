"""
Deploy backend to Render using Render API.
"""

import requests
import json
import os

# Render API configuration
RENDER_API_KEY = "rnd_bo83rX7s8bPZB3zcWEN3ZM6sN67z"
RENDER_API_URL = "https://api.render.com/v1"

# Headers for API requests
headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Content-Type": "application/json"
}

def create_render_service():
    """Create a new web service on Render."""
    
    # Service configuration
    service_data = {
        "type": "web_services",
        "name": "zero-orchestrator-api",
        "ownerId": "uid",  # Will be replaced with actual owner ID
        "repo": "your-repo-url",  # Need to replace with actual repo
        "branch": "main",
        "rootDir": "backend",
        "envVars": [
            {
                "key": "DATABASE_URL",
                "value": "postgresql://postgres:[YOUR-PASSWORD]@db.xvvpmofnuvptnbhkvazg.supabase.co:5432/postgres"
            },
            {
                "key": "SUPABASE_URL",
                "value": "https://xvvpmofnuvptnbhkvazg.supabase.co"
            },
            {
                "key": "SUPABASE_SERVICE_ROLE_KEY",
                "value": "sb_publishable_HK5uxbM2U7q13aK9NGQYHA_36qnmqAM"
            },
            {
                "key": "SECRET_KEY",
                "value": "zero-terminal-production-secret-key-2024"
            },
            {
                "key": "ALLOWED_ORIGINS",
                "value": "https://zero-orchestrator.vercel.app"
            },
            {
                "key": "PYTHON_VERSION",
                "value": "3.13"
            }
        ],
        "buildCommand": "pip install -r requirements.txt",
        "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
        "runtime": "python"
    }
    
    try:
        response = requests.post(
            f"{RENDER_API_URL}/services",
            headers=headers,
            json=service_data
        )
        
        if response.status_code == 201:
            print("✅ Render service created successfully!")
            print(f"Service URL: {response.json().get('service', {}).get('url')}")
            return response.json()
        else:
            print(f"❌ Failed to create Render service: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating Render service: {e}")
        return None


if __name__ == "__main__":
    print("Deploying Zero Orchestrator Backend to Render...")
    print("=" * 60)
    
    # Note: Render API deployment requires a connected GitHub repository
    # This script provides the configuration, but manual setup may be needed
    print("⚠️  Note: Render API deployment requires a GitHub repository.")
    print("Please follow these steps for manual deployment:")
    print("")
    print("1. Push your code to GitHub")
    print("2. Go to Render dashboard: https://dashboard.render.com")
    print("3. Click 'New +' → 'Web Service'")
    print("4. Connect your GitHub repository")
    print("5. Configure with these settings:")
    print("   - Root Directory: backend")
    print("   - Build Command: pip install -r requirements.txt")
    print("   - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT")
    print("6. Add these environment variables:")
    print("   - DATABASE_URL: postgresql://postgres:[YOUR-PASSWORD]@db.xvvpmofnuvptnbhkvazg.supabase.co:5432/postgres")
    print("   - SUPABASE_URL: https://xvvpmofnuvptnbhkvazg.supabase.co")
    print("   - SUPABASE_SERVICE_ROLE_KEY: sb_publishable_HK5uxbM2U7q13aK9NGQYHA_36qnmqAM")
    print("   - SECRET_KEY: zero-terminal-production-secret-key-2024")
    print("   - ALLOWED_ORIGINS: https://zero-orchestrator.vercel.app")
    print("   - PYTHON_VERSION: 3.13")
    print("")
    print("=" * 60)
