"""
QueryRouter — LLM-based intent classifier.

Classifies incoming user queries into routing intents:
  - "rag"       → simple lookup / definition / metadata (vector similarity)
  - "traversal" → structural / relational / impact analysis (graph walk)

Designed to be extended with a third intent ("write") when Temporal
workflow execution is ready.
"""

import json
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


# Supported intents — add "write" here when Temporal is ready
Intent = Literal["rag", "traversal"]

CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a query intent classifier for an infrastructure knowledge platform.

Classify the user's question into EXACTLY ONE of these categories:

**rag** — The user is asking a simple lookup, definition, or metadata question.
Examples:
  - "What is the API gateway?"
  - "Describe the load balancer configuration"
  - "What services do we run?"
  - "Tell me about our RDS instance"

**traversal** — The user is asking about relationships, dependencies, impact, flow, or paths between components.
Examples:
  - "What depends on the database?"
  - "What breaks if Redis goes down?"
  - "How does the frontend connect to the payment service?"
  - "Show me the dependency chain for the auth service"
  - "What is the blast radius of the API gateway failing?"
  - "What are the upstream services of the worker?"

Respond with ONLY a JSON object: {{"intent": "rag"}} or {{"intent": "traversal"}}
Do NOT include any other text."""),
    ("user", "{query}"),
])


class QueryRouter:
    """
    Routes queries to the appropriate processing path.
    Uses the LLM for classification with a structured-output prompt.
    Falls back to 'rag' on any parse error — safe default.
    """

    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.chain = CLASSIFICATION_PROMPT | self.llm

    def classify(self, query: str) -> Intent:
        """Classify a user query into 'rag' or 'traversal'."""
        try:
            response = self.chain.invoke({"query": query})
            content = response.content.strip()

            # Try parsing JSON
            parsed = json.loads(content)
            intent = parsed.get("intent", "rag")

            if intent in ("rag", "traversal"):
                return intent  # type: ignore[return-value]

            return "rag"

        except (json.JSONDecodeError, KeyError, AttributeError, Exception):
            # Any failure → safe fallback to RAG
            return "rag"
