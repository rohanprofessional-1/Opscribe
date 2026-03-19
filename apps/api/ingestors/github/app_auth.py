import os
import time
import jwt
import httpx
from typing import Optional
from dotenv import dotenv_values

def get_app_jwt() -> str:
    """
    Generates a short-lived JSON Web Token (JWT) signed with the GitHub App's Private Key.
    This JWT authenticates opscribe *as* the App itself.
    """
    # Use dotenv_values to properly parse the multiline unescaped RSA key
    env_vars = dotenv_values("apps/api/.env")
    
    app_id = env_vars.get("GITHUB_APP_ID") or os.environ.get("GITHUB_APP_ID")
    private_key = env_vars.get("GITHUB_APP_PRIVATE_KEY") or os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
    private_key = private_key.replace("\\n", "\n")

    if not app_id or not private_key:
        raise ValueError("Missing GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY in environment variables.")

    now = int(time.time())
    payload = {
        "iat": now - 60,       # Issued at time (60 seconds in the past to account for clock drift)
        "exp": now + (10 * 60), # Expiration time (10 minutes)
        "iss": app_id          # Issuer (the App ID)
    }

    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    return encoded_jwt

async def get_installation_token(installation_id: str) -> str:
    """
    Exchanges the App JWT for a short-lived Installation Access Token.
    This token is scoped strictly to the repositories authorized for this installation.
    """
    app_jwt = get_app_jwt()
    
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {app_jwt}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        
        if response.status_code != 201:
            raise Exception(f"Failed to generate Installation Token: {response.text}")
            
        return response.json()["token"]
