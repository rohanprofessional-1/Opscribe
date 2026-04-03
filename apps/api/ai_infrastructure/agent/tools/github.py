from langchain.tools import BaseTool, tool
from sqlmodel import Session
from uuid import UUID

def get_github_actions_tool(session: Session, tenant_id: UUID) -> BaseTool:
    """
    Tool that interacts with a user's GitHub Actions via the Opscribe Installation Token.
    """
    
    @tool("github_actions_manager", return_direct=True)
    def github_actions_manager(action: str, repo: str, workflow_id: str = "") -> str:
        """
        Interacts with GitHub Actions.
        Inputs:
        - action: Must be 'list' (list workflows) or 'trigger' (trigger a workflow run).
        - repo: The repository name (e.g., 'owner/repo').
        - workflow_id: The ID or filename of the workflow to trigger (only needed for 'trigger').
        """
        # Phase 1: Skeleton output
        # Phase 2: Use apps.api.ingestors.github.app_auth.get_installation_token
        
        if action == "list":
            return f"Simulating: Fetched workflows for `{repo}`.\n\n- build.yml (ID: 123) - Status: Success\n- deploy.yml (ID: 456) - Status: Failed"
            
        elif action == "trigger":
            if not workflow_id:
                return "Error: You must provide a workflow_id to trigger a workflow."
            return f"Simulating: Successfully triggered workflow `{workflow_id}` on `{repo}`. You can monitor the status on GitHub."
            
        return "Unknown action. Valid actions are 'list' or 'trigger'."
        
    return github_actions_manager
