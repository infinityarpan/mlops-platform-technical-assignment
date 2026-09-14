from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from app.domain.enums import LifecycleStage


@dataclass
class ModelRecord:
    id: str
    name: str
    owner: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    versions: list["VersionRecord"] = field(default_factory=list)


@dataclass
class VersionRecord:
    id: str
    model_id: str
    version: str
    framework: Optional[str]
    algorithm: Optional[str]
    artifact_uri: str
    training_data_ref: Optional[str]
    tags: list[str]
    extra_metadata: dict[str, Any]
    lifecycle_stage: LifecycleStage
    lock_version: int
    created_at: datetime
    updated_at: datetime
    mlflow_version: str
