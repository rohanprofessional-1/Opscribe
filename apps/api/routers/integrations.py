from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from apps.api.database import get_session
from apps.api.models import ClientIntegration
from apps.api.utils.encryption import encrypt_dict

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
SENSITIVE_KEYS = ["aws_secret_access_key", "secret_key", "minio_secret_key", "role_arn", "external_id"]

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
def save_integration(
    provider: str,
    config: IntegrationConfig,
    client_id: str,
    session: Session = Depends(get_session)
):
    """Save or update an integration configuration (e.g. AWS credentials)."""
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
