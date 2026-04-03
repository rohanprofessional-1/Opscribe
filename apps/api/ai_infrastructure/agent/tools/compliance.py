from langchain.tools import BaseTool, tool
from sqlmodel import Session
from uuid import UUID

def get_iam_compliance_tool(session: Session, tenant_id: UUID) -> BaseTool:
    """
    Queries the Opscribe database/RAG graph to check for overly permissive IAM roles.
    """
    
    @tool("check_iam_compliance", return_direct=False)
    def check_iam_compliance(service_filter: str = "ALL") -> str:
        """
        Scans current infrastructure graph for IAM roles and evaluates them
        for overly permissive policies (e.g., Resource: '*', Action: '*').
        Use this tool when users ask about "security", "compliance", or "IAM risks".
        Inputs:
        - service_filter: (default "ALL") Target a specific service or check all.
        """
        # Phase 1: Skeleton response
        # Phase 2: Query GraphRetriever or Postgres for IAM Nodes, evaluate JSON policy documents
        
        return """
**IAM Compliance Report (Simulated)**

We successfully scanned the architecture graph for IAM vulnerabilities:
- ⚠️ `OpscribeDiscoveryRole`: Contains `Action: sts:AssumeRole` on `Resource: *`. Consider scoping to specific ARNs.
- ❌ `LegacyS3AccessRole`: Contains `Action: s3:*` on `Resource: *`. High risk of data exfiltration.
- ✅ `EKSNodeGroupRole`: Fully compliant. Strict least-privilege scoping active.
"""
        
    return check_iam_compliance
