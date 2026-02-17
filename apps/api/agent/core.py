from typing import List
import os

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage

from apps.api.agent.tools import CreateNodeTool, ListNodesTool, RAGTool

def get_agent_executor() -> AgentExecutor:
    """
    Initializes and returns the LangChain AgentExecutor with tools and LLM.
    """
    # Ensure API Key is set
    if not os.environ.get("OPENAI_API_KEY"): # needs to change in future
        # For development/demo, we might warn or error. 
        # Assuming it's in env or .env file loaded by main.py
        pass

    llm = ChatOpenAI(model="gpt-4", temperature=0)

    tools = [
        CreateNodeTool(),
        ListNodesTool(),
        RAGTool()
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI assistant for Opscribe, an infrastructure knowledge platform. "
                   "You have access to tools to manage nodes and graphs, and to search the knowledge base. "
                   "When asked to create a node, ensure you have all necessary information. "
                   "Use the RAG tool to answer questions about the infrastructure based on existing knowledge."),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors=True
    )

    return agent_executor
