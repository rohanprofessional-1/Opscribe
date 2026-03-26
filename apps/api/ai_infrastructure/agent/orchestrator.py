from typing import List, Dict, Any, Optional
from uuid import UUID
import os

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from sqlmodel import Session

# Import tools (these will be built out individually)
from apps.api.infrastructure.agent.tools.rag import get_rag_search_tool
from apps.api.infrastructure.agent.tools.terraform import get_terraform_generator_tool
from apps.api.infrastructure.agent.tools.github import get_github_actions_tool
from apps.api.infrastructure.agent.tools.compliance import get_iam_compliance_tool

class AgentOrchestrator:
    """
    Replaces the legacy ChatService. 
    This Orchestrator provides the LLM with a suite of tools it can use 
    to interact with the infrastructure, generate files, and trigger workflows.
    """
    def __init__(self, session: Session, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id
        
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = "llama-3.3-70b-versatile"
        
        if self.api_key:
            # We use an LLM that supports Tool Calling natively
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
            get_iam_compliance_tool(session, tenant_id)
        ]
        
        self._setup_agent()

    def _setup_agent(self):
        if not self.llm:
            return

        # System prompt defines the persona and rules for tool usage
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the **Opscribe Enterprise Architect & Agent**. 

Your MAJOR priority is **Explanation and Action**. You make difficult infrastructure concepts easy for *anyone* to understand, and you take action on their behalf.

### COMMANDMENTS:
- **Analogy-Led Learning**: Use real-world analogies.
- **Plain English**: Avoid strict jargon unless defined.
- **Action-Oriented**: If the user asks for a Terraform file or a GitHub action, use your tools to do it. Do not just output the code in chat; use the tool to write the file or trigger the workflow.
- **Always Search First**: If the user asks about their infrastructure, ALWAYS use the RAG Search tool first before answering.

### STAKEHOLDER DOCS
If asked for a stakeholder doc or runbook, generate a highly structured markdown response highlighting business impact.
"""),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Bind the tools to the LLM to create an agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        # The Executor handles the loop of (Thought -> Action -> Observation -> Answer)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def run(self, query: str) -> str:
        if not self.llm:
            return "Error: GROQ_API_KEY not found in environment variables."
            
        response = self.agent_executor.invoke({"input": query})
        return response.get("output", "I could not generate a response.")
