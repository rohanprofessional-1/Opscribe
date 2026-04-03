"""
WorkflowSpec — structured payload for write-path intents.

This is the DATA CONTRACT between the Orchestrator Agent and the
(future) Temporal Execution Orchestrator. When the agent determines
the user wants to mutate infrastructure, it emits a WorkflowSpec
instead of executing directly.

Current status: STUB — schema defined, not yet emitted or consumed.
Next step: wire the Temporal worker to consume these payloads.
"""

from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field


class WorkflowSpec(BaseModel):
    """
    Structured payload describing an infrastructure mutation.

    Examples:
      - Provision a new Redis cluster via Terraform
      - Scale an ECS service via Pulumi
      - Roll back a Helm release
    """

    action: Literal["provision", "scale", "destroy", "migrate", "rollback", "update"]
    tool: Literal["terraform", "pulumi", "helm", "cdk", "cloudformation"]
    target_nodes: List[str] = Field(
        description="Node keys from the architecture graph that this workflow affects."
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific parameters (e.g., instance_type, replica_count)."
    )
    requires_approval: bool = Field(
        default=True,
        description="If True, a human must approve before execution."
    )
    dry_run: bool = Field(
        default=True,
        description="If True, the workflow only plans/previews without applying."
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable summary of what this workflow will do."
    )
