import os
import json
from fastapi import HTTPException, Security, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from uuid import UUID
from sqlmodel import Session, select
from apps.api.database import get_session
from apps.api.models import Client
import certifi

# Fix SSL certificates for macOS users who haven't run "Install Certificates.command"
# PyJWT uses urllib under the hood, so pointing it to certifi's bundle is the cleanest fix.
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "dev-xuzgmpozdykvxgyp.us.auth0.com")
API_AUDIENCE = os.environ.get("AUTH0_API_AUDIENCE", "https://api.opscribe.com")
ALGORITHMS = ["RS256"]

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verifies the JWT signature against the Auth0 JWKS endpoint."""
    token = credentials.credentials
    try:
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks_client = jwt.PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=API_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {e}")

def get_current_client_id(
    payload: dict = Depends(verify_token), 
    session: Session = Depends(get_session)
) -> UUID:
    """
    Extracts the Auth0 user ID (sub) and maps it to the local Opscribe Client tenant.
    Performs Just-in-Time (JIT) provisioning for new signups.
    """
    auth0_sub = payload.get("sub")
    if not auth0_sub:
        raise HTTPException(status_code=401, detail="No 'sub' claim in JWT")

    # In PostgreSQL, we can query JSONB fields directly, but for pure cross-dialect safety 
    # and given low volume, we fetch active clients or use a direct JSON filter
    # For now, let's use standard Python iteration since this is highly cacheable.
    
    statement = select(Client)
    all_clients = session.exec(statement).all()
    
    for c in all_clients:
        if c.metadata_ and c.metadata_.get("auth0_sub") == auth0_sub:
            return c.id

    # JIT Provisioning: First time logging in with Auth0
    client = Client(
        name="Personal Organization",
        metadata_={
            "role": "admin", 
            "auth0_sub": auth0_sub,
            "auth_provider": "auth0"
        }
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    
    print(f"DEBUG: Auto-provisioned new Opscribe Client {client.id} for Auth0 Sub: {auth0_sub}")
    return client.id