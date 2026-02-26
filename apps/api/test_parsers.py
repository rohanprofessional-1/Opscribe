import asyncio
import os
from apps.api.infrastructure.parsers.models import InfrastructureSignal
from apps.api.infrastructure.parsers.deterministic import IaCParser, DependencyParser
from apps.api.infrastructure.parsers.semantic import SemanticParser
from apps.api.infrastructure.parsers.aggregator import SignalAggregator

async def test_parsing_pipeline():
    print("=== Testing IaC Parser (Terraform) ===")
    tf_content = """
    resource "aws_db_instance" "prod_db" {
      engine = "postgres"
      instance_class = "db.t3.micro"
    }
    resource "aws_elasticache_cluster" "redis" {
      engine = "redis"
    }
    """
    iac_parser = IaCParser()
    signals_iac = iac_parser.parse_terraform("main.tf", tf_content)
    for s in signals_iac:
        print(f"  -> Found: {s.component_type} | {s.name} | Confidence: {s.confidence_score}")

    print("\n=== Testing Dependency Parser ===")
    req_content = """
    sqlalchemy==2.0.0
    redis-py>=4.0.0
    boto3
    """
    dep_parser = DependencyParser()
    signals_dep = dep_parser.parse_requirements_txt("requirements.txt", req_content)
    for s in signals_dep:
        print(f"  -> Found: {s.component_type} | {s.name} | Confidence: {s.confidence_score}")

    print("\n=== Testing Semantic Parser (LLM) ===")
    py_content = """
import os
import redis
from sqlalchemy import create_engine

# Connect to our primary database
engine = create_engine(os.environ.get("DATABASE_URL"))
cache = redis.from_url(os.environ.get("REDIS_URL"))
    """
    semantic_parser = SemanticParser(model="llama3.2")
    
    print("  -> Executing LLM parsing locally via Ollama (Requires 'ollama run llama3.2' active)")
    signals_sem = await semantic_parser.parse_application_code([{"path": "main.py", "content": py_content}])
    
    if not signals_sem:
         print("  -> Semantic Parser failed to return nodes. Ensure Ollama is running and model exists.")
         signals_sem = [
            InfrastructureSignal(component_type="Database", name="primary database", config={}, source_location="main.py", confidence_score=0.6),
            InfrastructureSignal(component_type="Cache", name="redis cache", config={}, source_location="main.py", confidence_score=0.6)
         ]
         print("  -> Injected fallback mock nodes to complete the test pipeline.")
    else:
        for s in signals_sem:
             print(f"  -> Found: {s.component_type} | {s.name} | Confidence: {s.confidence_score}")

    print("\n=== Testing Signal Aggregator (Deduplication) ===")
    all_signals = signals_iac + signals_dep + signals_sem
    print(f"Total raw signals before deduplication: {len(all_signals)}")
    
    aggregator = SignalAggregator(match_threshold=40) 
    final_nodes = aggregator.aggregate(all_signals)
    
    print(f"Total resolved nodes after deduplication: {len(final_nodes)}")
    for s in final_nodes:
        print(f"  => Node: {s.component_type} | {s.name} | Sources: {s.source_location}")

if __name__ == "__main__":
    asyncio.run(test_parsing_pipeline())
