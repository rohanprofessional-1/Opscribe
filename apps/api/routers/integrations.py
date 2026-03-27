from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel

from apps.api.database import get_session
from apps.api.models import ClientIntegration
from apps.api.utils.encryption import encrypt_dict

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
)

class IntegrationResponse(BaseModel):
    provider: str
    is_active: bool
    configured_keys: List[str]

class IntegrationConfig(BaseModel):
    credentials: Dict[str, Any]

# Keys that must be encrypted before saving to the database
SENSITIVE_KEYS = [
    "aws_secret_access_key", "secret_key", "minio_secret_key", "role_arn", "external_id",
    "github_private_key", "github_webhook_secret", "github_client_secret"
]

@router.get("/", response_model=List[IntegrationResponse])
def get_integrations(
    client_id: str,
    session: Session = Depends(get_session)
):
    """Get all configured integrations for the current client, masking secrets."""
    statement = select(ClientIntegration).where(
        ClientIntegration.client_id == client_id,
        ClientIntegration.is_active == True
    )
    integrations = session.exec(statement).all()
    
    results = []
    for integration in integrations:
        # We only return the keys of the credentials json to show it's configured,
        # but avoid returning the actual secret values.
        results.append(IntegrationResponse(
            provider=integration.provider,
            is_active=integration.is_active,
            configured_keys=list(integration.credentials.keys())
        ))
    
    return results

@router.post("/{provider}")
async def save_integration(
    provider: str,
    config: IntegrationConfig,
    client_id: str,
    session: Session = Depends(get_session)
):
    """Save or update an integration configuration (e.g. AWS credentials)."""
    
    # Pre-flight Validation for AWS
    if provider == "aws":
        try:
            from apps.api.ingestors.aws.detector import AWSDetector
            region = config.credentials.get("region", "us-east-1")
            # If standard STS fails, _get_account_id gracefully falls back to 000000000000
            # but we explicitly want to block invalid credentials here.
            detector = AWSDetector(region_name=region, credentials=config.credentials)
            account_id = detector._get_account_id()
            if account_id == "000000000000":
                raise ValueError("Invalid IAM Role or Access Keys. Connection could not be established.")
        except Exception as e:
            # We raise an HTTP error so the frontend catches it and displays it
            raise HTTPException(status_code=400, detail=str(e))
            
    # Pre-flight validation & Auto-Discovery for GitHub App
    elif provider == "github_app":
        try:
            import httpx
            import time
            import jwt
            
            app_id = config.credentials.get("github_app_id", "").strip()
            pem = config.credentials.get("github_private_key", "").strip()
            
            if not app_id or not pem:
                raise ValueError("Missing App ID or Private Key.")
                
            # Normalise PEM format
            if pem.startswith("----BEGIN") and not pem.startswith("-----BEGIN"):
                pem = "-" + pem
                config.credentials["github_private_key"] = pem
            pem = pem.replace("\\n", "\n")
            
            # Ensure valid signature
            try:
                now = int(time.time())
                payload = {"iat": now - 60, "exp": now + (10 * 60), "iss": app_id}
                jwt_token = jwt.encode(payload, pem, algorithm="RS256")
            except Exception as e:
                raise ValueError(f"Failed to generate JWT with provided Private Key: {str(e)}")
                
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            # Use async httpx client instead of blocking requests
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.github.com/app/installations", headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    installations = response.json()
                    if installations:
                        # Auto-link the primary installation ID found
                        installation_id = str(installations[0].get("id"))
                        from apps.api.models import Client
                        db_client = session.get(Client, client_id)
                        if db_client:
                            db_client.metadata_ = dict(db_client.metadata_ or {})
                            db_client.metadata_["github_installation_id"] = installation_id
                            session.add(db_client)
                            logger.info(f"Automatically linked GitHub installation {installation_id} for client {client_id}")
                else:
                    detail = response.json().get("message", "Unknown GitHub Error") if response.status_code != 401 else "Invalid App ID or Private Key"
                    raise ValueError(f"GitHub Validation Failed: {detail}")
                    
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"GitHub App pre-flight validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to validate credentials: {str(e)}")

    statement = select(ClientIntegration).where(
        ClientIntegration.client_id == client_id,
        ClientIntegration.provider == provider
    )
    existing = session.exec(statement).first()
    
    # Encrypt sensitive keys before saving
    safe_credentials = encrypt_dict(config.credentials, SENSITIVE_KEYS)
    
    if existing:
        existing.credentials = safe_credentials
        existing.is_active = True
        session.add(existing)
    else:
        new_integration = ClientIntegration(
            client_id=client_id,
            provider=provider,
            credentials=safe_credentials,
            is_active=True
        )
        session.add(new_integration)
        
    session.commit()
    return {"status": "success", "provider": provider}

@router.delete("/{provider}")
def remove_integration(
    provider: str,
    client_id: str,
    session: Session = Depends(get_session)
):
    """Deactivate an integration."""
    statement = select(ClientIntegration).where(
        ClientIntegration.client_id == client_id,
        ClientIntegration.provider == provider
    )
    existing = session.exec(statement).first()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    session.delete(existing)
    session.commit()
    return {"status": "deleted"}
