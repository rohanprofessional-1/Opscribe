from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from apps.api.database import get_session
from apps.api.ingestors.aws.manager import DiscoveryManager
from apps.api.ingestors.aws.detector import AWSDetector
from apps.api import schemas

router = APIRouter(
    prefix="/discovery",
    tags=["discovery"]
)

@router.post("/run")
async def run_discovery(
    request: schemas.DiscoveryRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Trigger a discovery run to populate nodes/edges in the specified graph.
    Set include_relationships=False for a 'datalake' style disjointed node population.
    """
    manager = DiscoveryManager(session)
    
    # Register AWS detector if requested
    if not request.source_names or "aws" in request.source_names:
        manager.register_detector(AWSDetector())
    
    # We run this as a background task because discovery can take time
    background_tasks.add_task(
        manager.run_discovery,
        client_id=request.client_id,
        graph_id=request.graph_id,
        source_names=request.source_names,
        include_relationships=request.include_relationships
    )
    
    return {"message": "Discovery started", "include_relationships": request.include_relationships}
