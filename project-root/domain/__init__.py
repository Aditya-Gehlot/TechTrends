"""Domain contracts for the TechTrends pipeline.

These objects are intentionally storage-agnostic. API, database, dashboard,
and file adapters can all depend on them without pulling in infrastructure
details.
"""

from domain.artifacts import (
    FeatureSnapshotContract,
    ModelMetadataContract,
    NormalizedRecordContract,
    PredictionContract,
    SourceSummaryContract,
)
from domain.pipeline import (
    PIPELINE_STAGE_DEFINITIONS,
    TERMINAL_PIPELINE_STATUSES,
    DatasetShape,
    PipelineRunContract,
    PipelineStageContract,
)

__all__ = [
    "DatasetShape",
    "FeatureSnapshotContract",
    "ModelMetadataContract",
    "NormalizedRecordContract",
    "PIPELINE_STAGE_DEFINITIONS",
    "PipelineRunContract",
    "PipelineStageContract",
    "PredictionContract",
    "SourceSummaryContract",
    "TERMINAL_PIPELINE_STATUSES",
]
