from .base import ProcessingContext
from .normalize import NormalizeStage
from .resolve import ResolveStage
from .enrich import EnrichStage
from .validate import ValidateStage

class InfrastructurePipeline:
    def __init__(self):
        self.stages = [
            NormalizeStage(),
            ResolveStage(),
            EnrichStage(),
            ValidateStage()
        ]

    def execute(self, raw_github: dict, raw_aws: dict) -> ProcessingContext:
        context = ProcessingContext(raw_github, raw_aws)
        for stage in self.stages:
            context = stage.run(context)
        return context
