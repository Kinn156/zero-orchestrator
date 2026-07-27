"""
Deploy frontend to Vercel using Vercel API.
"""

import requests
import json
import os

# Vercel API configuration
VERCEL_API_KEY = "vcp_10RI1Kr56LwPRzFRxmBZpm2rPXBi3bPOsTWTkq1yYzo89tpFfV1cBcfe"
VERCEL_API_URL = "https://api.vercel.com/v1"

# Headers for API requests
headers = {
    "Authorization": f"Bearer {VERCEL_API_KEY}",
    "Content-Type": "application/json"
}

def create_vercel_project():
    """Create a new project on Vercel."""
    
    # Project configuration
    project_data = {
        "name": "zero-orchestrator",
        "framework": "vite",
        "rootDirectory": "frontend",
        "buildCommand": "npm run build",
        "outputDirectory": "dist",
        "env": [
            {
                "key": "VITE_API_URL",
                "value": "https://zero-orchestrator-api.onrender.com",
                "type": "plain"
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{VERCEL_API_URL}/projects",
            headers=headers,
            json=project_data
        )
        
        if response.status_code == 201 or response.status_code == 200:
            print("✅ Vercel project created successfully!")
            print(f"Project URL: {response.json().get('url')}")
            return response.json()
        else:
            print(f"❌ Failed to create Vercel project: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating Vercel project: {e}")
        return None


if __name__ == "__main__":
    print("Deploying Zero Orchestrator Frontend to Vercel...")
    print("=" * 60)
    
    # Note: Vercel API deployment requires a connected GitHub repository
    # This script provides the configuration, but manual setup may be needed
    print("⚠️  Note: Vercel API deployment requires a GitHub repository.")
    print("Please follow these steps for manual deployment:")
    print("")
    print("1. Push your code to GitHub")
    print("2. Go to Vercel dashboard: https://vercel.com/dashboard")
    print("3. Click 'Add New Project'")
    print("4. Import your GitHub repository")
    print("5. Configure with these settings:")
    print("   - Root Directory: frontend")
    print("   - Framework Preset: Vite")
    print("   - Build Command: npm run build")
    print("   - Output Directory: dist")
    print("6. Add environment variable:")
    print("   - VITE_API_URL: https://zero-orchestrator-api.onrender.com")
    print("7. Click 'Deploy'")
    print("")
    print("=" * 60)
