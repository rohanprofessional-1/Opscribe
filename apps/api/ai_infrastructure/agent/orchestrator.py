from typing import List, Dict, Any, Optional
from uuid import UUID
import os

from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from sqlmodel import Session

# Import tools (these will be built out individually)
from apps.api.ai_infrastructure.agent.tools.rag import get_rag_search_tool
from apps.api.ai_infrastructure.agent.tools.terraform import get_terraform_generator_tool
from apps.api.ai_infrastructure.agent.tools.github import get_github_actions_tool
from apps.api.ai_infrastructure.agent.tools.compliance import get_iam_compliance_tool
from apps.api.ai_infrastructure.agent.tools.graph_tools import get_graph_traversal_tools

class AgentOrchestrator:
    """
    Orchestrator Agent with READ/WRITE separation:
      - READ: RAG search + graph traversal tools (no side effects)
      - WRITE: explains what would be done (WorkflowSpec emission comes later)
    """
    def __init__(self, session: Session, tenant_id: UUID, graph_id: Optional[UUID] = None):
        self.session = session
        self.tenant_id = tenant_id
        self.graph_id = graph_id
        
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.3-70b-versatile"
        
        if self.api_key:
            self.llm = ChatGroq(
                temperature=0, 
                groq_api_key=self.api_key, 
                model_name=self.model
            )
        else:
            self.llm = None

        # Load available tools using dependency injection for the DB session/tenant
        self.tools = [
            get_rag_search_tool(session, tenant_id),
            get_terraform_generator_tool(),
            get_github_actions_tool(session, tenant_id),
            get_iam_compliance_tool(session, tenant_id),
        ]

        # Add graph traversal tools if a graph_id is provided
        if graph_id:
            self.tools.extend(get_graph_traversal_tools(session, graph_id))
        
        self._setup_agent()

    def _setup_agent(self):
        if not self.llm:
            return

        system_prompt = (
            "You are the **Opscribe Enterprise Architect & Agent**.\n\n"
            "Your MAJOR priority is **Explanation and Action**. You make difficult "
            "infrastructure concepts easy for *anyone* to understand, and you take "
            "action on their behalf.\n\n"
            "### READ vs WRITE AWARENESS:\n"
            "- **READ Questions** (about existing infrastructure): Use RAG search and "
            "graph traversal tools. These are safe, read-only operations.\n"
            "- **WRITE Questions** (provisioning, scaling, destroying): Do NOT execute "
            "directly. Instead, describe what WOULD be done as a structured action plan. "
            "Explain the steps, the tools involved (Terraform, Helm, etc.), and what "
            "approval would be needed.\n\n"
            "### COMMANDMENTS:\n"
            "- **Analogy-Led Learning**: Use real-world analogies.\n"
            "- **Plain English**: Avoid strict jargon unless defined.\n"
            "- **Action-Oriented**: For read questions, use your tools to fetch real data. "
            "For write questions, explain the plan.\n"
            "- **Always Search First**: If the user asks about their infrastructure, "
            "ALWAYS use a search or traversal tool first before answering.\n"
            "- **Graph Traversal**: For dependency, impact, or flow questions, prefer "
            "graph traversal tools over RAG search.\n\n"
            "### STAKEHOLDER DOCS\n"
            "If asked for a stakeholder doc or runbook, generate a highly structured "
            "markdown response highlighting business impact.\n\n"
            "### CRITICAL TOOL BEHAVIOR:\n"
            "If you decide to invoke a tool, you MUST output ONLY the tool call. Do not provide any conversational text, explanations, or thoughts before calling the tool. Just directly execute the tool."
        )

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
        )

    def run(self, query: str) -> str:
        if not self.llm:
            return "Error: GROQ_API_KEY not found in environment variables."
            
        result = self.agent.invoke({"messages": [HumanMessage(content=query)]})
        
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                return last_msg.content
        
        return "I could not generate a response."


