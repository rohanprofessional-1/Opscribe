import time
import jwt
import httpx
from typing import Optional

# IMPORTANT: This module reads GitHub App credentials from the database (ClientIntegration table)
# rather than a global config or environment variables. Each client provides their own app credentials.

def get_app_jwt(client_id: str, session) -> str:
    """
    Generates a short-lived JWT signed with the client's custom GitHub App Private Key.
    Reads 'github_app_id' and 'github_private_key' from their ClientIntegration record.
    """
    from apps.api.models import ClientIntegration
    from apps.api.utils.encryption import decrypt_dict
    from apps.api.routers.integrations import SENSITIVE_KEYS
    from sqlmodel import select

    statement = select(ClientIntegration).where(
        ClientIntegration.client_id == client_id,
        ClientIntegration.provider == "github_app",
        ClientIntegration.is_active == True
    )
    integration = session.exec(statement).first()

    if not integration:
        raise ValueError(f"GitHub App credentials not found for client {client_id}. Please configure them in the Provider Settings.")

    creds = decrypt_dict(integration.credentials, SENSITIVE_KEYS)
    app_id = creds.get("github_app_id")
    private_key = creds.get("github_private_key")

    if not app_id or not private_key:
        raise ValueError(f"Incomplete GitHub App credentials for client {client_id}. Missing App ID or Private Key.")

    # Normalise any literal \n sequences (can appear when key is copy-pasted)
    private_key = private_key.replace("\\n", "\n")

    # Ensure valid PEM headers/footers in case it was saved before strict validation
    if private_key.startswith("----BEGIN") and not private_key.startswith("-----BEGIN"):
        private_key = "-" + private_key
        
    now = int(time.time())
    payload = {
        "iat": now - 60,        # 60 s in the past to avoid clock-drift rejection
        "exp": now + (10 * 60), # 10-minute expiry
        "iss": str(app_id),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: str, client_id: str, session) -> str:
    """
    Exchanges the client's App JWT for a short-lived Installation Access Token scoped to
    the repositories authorised for this installation.
    """
    app_jwt = get_app_jwt(client_id, session)

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {app_jwt}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)

        if response.status_code != 201:
            raise Exception(f"Failed to generate Installation Token: {response.text}")

        return response.json()["token"]
