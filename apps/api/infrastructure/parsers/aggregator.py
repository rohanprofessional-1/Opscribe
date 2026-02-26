from typing import List, Dict
from thefuzz import fuzz
from apps.api.infrastructure.parsers.models import InfrastructureSignal

class SignalAggregator:
    """
    Consolidates InfrastructureSignals from all strategies (A, B, C).
    Deduplicates overlapping signals (e.g., 'redis' package from B and 'redis_instance' from A)
    using fuzzy string matching and weighted confidence scoring.
    """
    
    def __init__(self, match_threshold: int = 85):
        self.match_threshold = match_threshold
        
    def aggregate(self, signals: List[InfrastructureSignal]) -> List[InfrastructureSignal]:
        if not signals:
            return []
            
        # Group signals implicitly by their architecture 'component_type' (e.g. Database, Cache)
        grouped_signals: Dict[str, List[InfrastructureSignal]] = {}
        for sig in signals:
            grouped_signals.setdefault(sig.component_type, []).append(sig)
            
        final_signals: List[InfrastructureSignal] = []
        
        for comp_type, group in grouped_signals.items():
            merged_group = self._deduplicate_group(group)
            final_signals.extend(merged_group)
            
        return final_signals

    def _deduplicate_group(self, group: List[InfrastructureSignal]) -> List[InfrastructureSignal]:
        """
        Takes a list of signals of the SAME component_type and merges duplicates.
        O(N^2) comparison is acceptable here because groups are typically small (1-10 items).
        """
        merged: List[InfrastructureSignal] = []
        
        for incoming in group:
            matched = False
            for existing in merged:
                # Compare semantic names using token_set_ratio for partial word matching (e.g. 'dep-sqlalchemy' vs 'prod_db')
                # We use token_set_ratio because it handles differences in string lengths better
                similarity = fuzz.token_set_ratio(incoming.name.lower(), existing.name.lower())
                
                # If they are the identical component type and their names share a high semantic similarity
                # OR if they are just generically named dependencies that match the component type, merge them
                if similarity >= self.match_threshold or ("dep" in incoming.name.lower() and existing.component_type == incoming.component_type):
                    matched = True
                    # A match is found! We need to merge them.
                    # 1. Keep the highest confidence score
                    # 2. Prefer the name of the higher confidence signal
                    # 3. Merge configs together
                    
                    if incoming.confidence_score > existing.confidence_score:
                        existing.name = incoming.name
                        existing.confidence_score = incoming.confidence_score
                        existing.source_location = f"{incoming.source_location}, {existing.source_location}"
                    
                    existing.config.update(incoming.config)
                    break 
            
            if not matched:
                merged.append(incoming)
                
        return merged
