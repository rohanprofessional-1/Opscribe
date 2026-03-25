from langchain.tools import BaseTool, tool
from sqlmodel import Session
from uuid import UUID

def get_rag_search_tool(session: Session, tenant_id: UUID) -> BaseTool:
    """
    Wraps the existing RAG GraphRetriever into a LangChain Tool.
    This allows the Agent to fetch real infrastructure context on demand.
    """
    
    @tool(name="search_infrastructure_graph", return_direct=False)
    def search_infrastructure_graph(query: str) -> str:
        """
        Searches the Opscribe vector database for infrastructure context.
        Use this tool EVERY TIME the user asks about their existing architecture,
        nodes, edges, or infrastructure components.
        """
        # In a full implementation, you'd import GraphRetriever here
        from apps.api.infrastructure.rag.retriever import GraphRetriever
        
        try:
            retriever = GraphRetriever(session)
            results = retriever.retrieve(query=query, tenant_id=tenant_id, limit=5)
            
            if not results:
                return "No relevant infrastructure context found."
                
            return "\n\n---\n\n".join([r.content for r in results])
        except Exception as e:
            return f"Error retrieving context: {str(e)}"
            
    return search_infrastructure_graph
