import os
import time
import jwt
import httpx
from typing import Optional

# IMPORTANT: This module reads GitHub App credentials from the database (platform_config table)
# rather than from environment variables. Credentials are configured via POST /admin/github-app.
# On first boot, main.py runs bootstrap_github_app_from_env() to seed from env if the table is empty.

def get_app_jwt(session) -> str:
    """
    Generates a short-lived JWT signed with the GitHub App's Private Key.
    Reads GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY from the platform_config DB table.
    """
    from apps.api.models import PlatformConfig
    from apps.api.utils.encryption import decrypt_value

    app_id_row = session.get(PlatformConfig, "github_app_id")
    private_key_row = session.get(PlatformConfig, "github_app_private_key")

    if not app_id_row or not private_key_row:
        raise ValueError(
            "GitHub App credentials not found in database. "
            "Configure them via POST /admin/github-app or set GITHUB_APP_ID and "
            "GITHUB_APP_PRIVATE_KEY in .env for bootstrap."
        )

    app_id = app_id_row.value
    private_key = decrypt_value(private_key_row.value)
    # Normalise any literal \n sequences (can appear when key is copy-pasted)
    private_key = private_key.replace("\\n", "\n")

    now = int(time.time())
    payload = {
        "iat": now - 60,        # 60 s in the past to avoid clock-drift rejection
        "exp": now + (10 * 60), # 10-minute expiry
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: str, session) -> str:
    """
    Exchanges the App JWT for a short-lived Installation Access Token scoped to
    the repositories authorised for this installation.
    """
    app_jwt = get_app_jwt(session)

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
