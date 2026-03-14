import os
import logging
from typing import List, Dict, Any

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from apps.api.infrastructure.parsers.models import InfrastructureSignal

logger = logging.getLogger(__name__)

class ExtractionResult(BaseModel):
    """Pydantic model representing the expected structured output from the LLM."""
    signals: List[InfrastructureSignal] = Field(
        default_factory=list, 
        description="The list of infrastructure components found in the code."
    )

class SemanticParser:
    """
    LLM-Assisted Semantic Extraction for Application Code.
    
    This strategy relies on local LLMs (via Ollama) and Structured Outputs 
    (via the `instructor` library) to semantically analyze application source code
    that lacks explicit infrastructure definitions. It identifies implicit architectural 
    dependencies such as external SDK calls, DSN strings, and port bindings.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3.2") -> None:
        """
        Initializes the Semantic Extractor to target an OpenAI-compatible endpoint.
        
        Args:
            base_url (str): The OpenAI-compatible API endpoint. Defaults to local Ollama.
            model (str): The local model to use. Defaults to 'llama3.2'.
        """
        api_key = os.environ.get("OPENAI_API_KEY", "ollama-local")
        
        # Instantiate base AsyncOpenAI client
        raw_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=3,
        )
        
        # Patch client with Instructor for Pydantic schema adherence
        # Mode.JSON forces the model to generate a raw JSON string validating against the schema
        self.client = instructor.patch(raw_client, mode=instructor.Mode.JSON)
        self.model = model

    async def parse_application_code(self, files: List[Dict[str, str]]) -> List[InfrastructureSignal]:
        """
        Analyzes a batch of application source code files to extract implied infrastructure signals.
        
        Args:
            files (List[Dict[str, str]]): Dictionaries containing 'path' and 'content' keys.
                                          
        Returns:
            List[InfrastructureSignal]: The mapped architectural components found.
        """
        if not files:
            return []

        prompt_context = self._build_prompt_context(files)

        try:
            extraction: ExtractionResult = await self.client.chat.completions.create(
                model=self.model,
                response_model=ExtractionResult,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a Senior Cloud Architect static analysis bot. You extract abstract infrastructure topologies from code."
                    },
                    {
                        "role": "user", 
                        "content": prompt_context
                    }
                ],
                temperature=0.0  # Force maximum determinism
            )
            
            self._backfill_source_locations(extraction.signals, [f.get("path", "unknown") for f in files])
            return extraction.signals

        except Exception as e:
            logger.error(f"Semantic parsing failed on model %s: %s", self.model, e)
            return []

    def _build_prompt_context(self, files: List[Dict[str, str]]) -> str:
        """Constructs the heavily instructed prompt body with the embedded code files."""
        context_parts = [
            "Analyze the following application source code files and extract the implied infrastructure components.\n"
        ]
        
        for f in files:
            path = f.get("path", "unknown")
            content = f.get("content", "")
            context_parts.append(f"--- FILE: {path} ---\n{content}\n")
            
        context_parts.append("""
CRITICAL INSTRUCTIONS:
- Look for external service calls (HTTP SDKs, DSN connection strings like postgres://).
- Look for environment variable references (e.g., REDIS_URL) that imply a dependency.
- Look for port bindings.
- Map what you find to abstract component_types like 'Database', 'Cache', 'Worker', 'Queue'.
- Set confidence_score between 0.4 and 0.7 since this is implicit semantic extraction.
- Output strictly in JSON format matching the schema.
        """)
        
        return "\n".join(context_parts)

    def _backfill_source_locations(self, signals: List[InfrastructureSignal], valid_paths: List[str]) -> None:
        """Ensures all extracted signals have a valid source_location (LLMs sometimes hallucinate this)."""
        fallback_path = valid_paths[0] if valid_paths else "unknown"
        for sig in signals:
            if not sig.source_location or not any(p in sig.source_location for p in valid_paths):
                sig.source_location = fallback_path
