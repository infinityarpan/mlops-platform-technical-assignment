from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from mlflow.exceptions import MlflowException, RestException
from mlflow.tracking import MlflowClient

from app.config import settings
from app.domain.enums import (
    PRODUCTION_ALIAS,
    STAGING_ALIAS,
    TAG_ARCHIVED,
    LifecycleStage,
)
from app.domain.errors import ConflictError, NotFoundError
from app.domain.lifecycle import assert_can_promote, assert_can_promote_to_staging
from app.services.registry_records import ModelRecord, VersionRecord

logger = structlog.get_logger()

TAG_OWNER = "mlops.owner"
TAG_DESCRIPTION = "mlops.description"
TAG_DISPLAY_NAME = "mlops.display_name"
TAG_SEMANTIC_VERSION = "mlops.semantic_version"
TAG_LOCK_VERSION = "mlops.lock_version"
TAG_FRAMEWORK = "mlops.framework"
TAG_ALGORITHM = "mlops.algorithm"
TAG_TRAINING_DATA = "mlops.training_data_ref"
TAG_EXTRA_METADATA = "mlops.extra_metadata"
TAG_USER_TAGS = "mlops.user_tags"


def _ms_to_datetime(value: int | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _tag_map(tags: list | dict | None) -> dict[str, str]:
    if not tags:
        return {}
    if isinstance(tags, dict):
        return {str(key): str(value) for key, value in tags.items()}
    return {tag.key: tag.value for tag in tags}


def _version_id(model_id: str, mlflow_version: str) -> str:
    return f"{model_id}/{mlflow_version}"


def _is_not_found(exc: Exception) -> bool:
    if isinstance(exc, RestException) and exc.error_code == "RESOURCE_DOES_NOT_EXIST":
        return True
    return isinstance(exc, MlflowException) and "not found" in str(exc).lower()


def _is_already_exists(exc: Exception) -> bool:
    if isinstance(exc, RestException) and exc.error_code == "RESOURCE_ALREADY_EXISTS":
        return True
    return isinstance(exc, MlflowException) and "already exists" in str(exc).lower()


class MLflowRegistry:
    """MLflow 3 registry using aliases (staging/production) and archived tags."""

    def __init__(self, client: MlflowClient | None = None) -> None:
        self._client = client or MlflowClient(tracking_uri=settings.mlflow_tracking_uri)

    def _get_registered_model(self, model_id: str):
        try:
            return self._client.get_registered_model(model_id)
        except (RestException, MlflowException) as exc:
            if _is_not_found(exc):
                raise NotFoundError("Model not found", f"No model exists with id '{model_id}'.") from exc
            raise

    def _search_model_versions(self, model_id: str):
        return self._client.search_model_versions(f"name='{model_id}'")

    def _get_model_version(self, model_id: str, mlflow_version: str):
        try:
            return self._client.get_model_version(model_id, mlflow_version)
        except (RestException, MlflowException) as exc:
            if _is_not_found(exc):
                raise NotFoundError(
                    "Version not found",
                    f"Model '{model_id}' has no MLflow version '{mlflow_version}'.",
                ) from exc
            raise

    def _find_by_semantic_version(self, model_id: str, semantic_version: str):
        for model_version in self._search_model_versions(model_id):
            tags = _tag_map(model_version.tags)
            if tags.get(TAG_SEMANTIC_VERSION) == semantic_version:
                return model_version
        raise NotFoundError(
            "Version not found",
            f"Model '{model_id}' has no version '{semantic_version}'.",
        )

    def _lifecycle_from_version(self, model_version) -> LifecycleStage:
        tags = _tag_map(model_version.tags)
        if tags.get(TAG_ARCHIVED) == "true":
            return LifecycleStage.ARCHIVED
        aliases = list(model_version.aliases or [])
        if PRODUCTION_ALIAS in aliases:
            return LifecycleStage.PRODUCTION
        if STAGING_ALIAS in aliases:
            return LifecycleStage.STAGING
        return LifecycleStage.NONE

    def _clear_aliases_on_version(self, model_id: str, mlflow_version: str) -> None:
        for alias in (STAGING_ALIAS, PRODUCTION_ALIAS):
            try:
                current = self._client.get_model_version_by_alias(model_id, alias)
            except (RestException, MlflowException):
                continue
            if current.version == mlflow_version:
                self._client.delete_registered_model_alias(model_id, alias)

    def _apply_lifecycle(self, model_id: str, mlflow_version: str, target: LifecycleStage) -> None:
        if target == LifecycleStage.NONE:
            self._clear_aliases_on_version(model_id, mlflow_version)
            self._client.set_model_version_tag(model_id, mlflow_version, TAG_ARCHIVED, "false")
            return
        if target == LifecycleStage.ARCHIVED:
            self._clear_aliases_on_version(model_id, mlflow_version)
            self._client.set_model_version_tag(model_id, mlflow_version, TAG_ARCHIVED, "true")
            return

        self._client.set_model_version_tag(model_id, mlflow_version, TAG_ARCHIVED, "false")
        try:
            if target == LifecycleStage.STAGING:
                self._client.set_registered_model_alias(model_id, STAGING_ALIAS, mlflow_version)
            elif target == LifecycleStage.PRODUCTION:
                self._client.set_registered_model_alias(model_id, PRODUCTION_ALIAS, mlflow_version)
        except (RestException, MlflowException) as exc:
            raise ConflictError(
                "mlflow-alias-failed",
                "MLflow alias update failed",
                str(exc),
            ) from exc

    def _to_model_record(self, registered_model, *, include_versions: bool = False) -> ModelRecord:
        tags = _tag_map(registered_model.tags)
        created = _ms_to_datetime(registered_model.creation_timestamp)
        updated = _ms_to_datetime(registered_model.last_updated_timestamp or registered_model.creation_timestamp)
        record = ModelRecord(
            id=registered_model.name,
            name=tags.get(TAG_DISPLAY_NAME, registered_model.name),
            owner=tags.get(TAG_OWNER, "unknown"),
            description=tags.get(TAG_DESCRIPTION),
            created_at=created,
            updated_at=updated,
        )
        if include_versions:
            versions = [
                self._to_version_record(model_version, registered_model.name)
                for model_version in sorted(
                    self._search_model_versions(registered_model.name),
                    key=lambda item: int(item.version),
                )
            ]
            record.versions = versions
        return record

    def _to_version_record(self, model_version, model_id: str) -> VersionRecord:
        tags = _tag_map(model_version.tags)
        extra_metadata_raw = tags.get(TAG_EXTRA_METADATA, "{}")
        try:
            extra_metadata = json.loads(extra_metadata_raw)
        except json.JSONDecodeError:
            extra_metadata = {}
        user_tags_raw = tags.get(TAG_USER_TAGS, "[]")
        try:
            user_tags = json.loads(user_tags_raw)
        except json.JSONDecodeError:
            user_tags = []
        created = _ms_to_datetime(model_version.creation_timestamp)
        updated = _ms_to_datetime(model_version.last_updated_timestamp or model_version.creation_timestamp)
        lock_version = int(tags.get(TAG_LOCK_VERSION, "1"))
        return VersionRecord(
            id=_version_id(model_id, model_version.version),
            model_id=model_id,
            version=tags.get(TAG_SEMANTIC_VERSION, model_version.version),
            framework=tags.get(TAG_FRAMEWORK) or None,
            algorithm=tags.get(TAG_ALGORITHM) or None,
            artifact_uri=model_version.source,
            training_data_ref=tags.get(TAG_TRAINING_DATA) or None,
            tags=user_tags,
            extra_metadata=extra_metadata,
            lifecycle_stage=self._lifecycle_from_version(model_version),
            lock_version=lock_version,
            created_at=created,
            updated_at=updated,
            mlflow_version=model_version.version,
        )

    def create_model(self, payload) -> ModelRecord:
        tags = {
            TAG_DISPLAY_NAME: payload.name,
            TAG_OWNER: payload.owner,
        }
        if payload.description:
            tags[TAG_DESCRIPTION] = payload.description
        try:
            registered = self._client.create_registered_model(payload.id, tags=tags)
        except (RestException, MlflowException) as exc:
            if _is_already_exists(exc):
                raise ConflictError(
                    "model-exists",
                    "Model already exists",
                    f"Model '{payload.id}' is already registered.",
                ) from exc
            raise
        logger.info("model_created", model_id=registered.name)
        return self._to_model_record(registered)

    def list_models(self) -> list[ModelRecord]:
        models = self._client.search_registered_models()
        records = [self._to_model_record(model) for model in models]
        return sorted(records, key=lambda item: item.name.lower())

    def get_model(self, model_id: str, *, include_versions: bool = False) -> ModelRecord:
        registered = self._get_registered_model(model_id)
        return self._to_model_record(registered, include_versions=include_versions)

    def register_version(self, model_id: str, payload) -> VersionRecord:
        self._get_registered_model(model_id)
        for existing in self._search_model_versions(model_id):
            tags = _tag_map(existing.tags)
            if tags.get(TAG_SEMANTIC_VERSION) == payload.version:
                raise ConflictError(
                    "version-exists",
                    "Version already exists",
                    f"Version '{payload.version}' is already registered for '{model_id}'.",
                )
        tags = {
            TAG_SEMANTIC_VERSION: payload.version,
            TAG_ARCHIVED: "false",
            TAG_LOCK_VERSION: "1",
            TAG_USER_TAGS: json.dumps(payload.tags),
            TAG_EXTRA_METADATA: json.dumps(payload.extra_metadata),
        }
        if payload.framework:
            tags[TAG_FRAMEWORK] = payload.framework
        if payload.algorithm:
            tags[TAG_ALGORITHM] = payload.algorithm
        if payload.training_data_ref:
            tags[TAG_TRAINING_DATA] = payload.training_data_ref
        model_version = self._client.create_model_version(
            name=model_id,
            source=payload.artifact_uri,
            tags=tags,
        )
        logger.info("version_registered", model_id=model_id, version=payload.version)
        fresh = self._get_model_version(model_id, model_version.version)
        return self._to_version_record(fresh, model_id)

    def list_versions(self, model_id: str) -> list[VersionRecord]:
        self._get_registered_model(model_id)
        records = []
        for model_version in sorted(self._search_model_versions(model_id), key=lambda item: int(item.version)):
            fresh = self._get_model_version(model_id, model_version.version)
            records.append(self._to_version_record(fresh, model_id))
        return records

    def get_version(self, model_id: str, version: str) -> VersionRecord:
        self._get_registered_model(model_id)
        model_version = self._find_by_semantic_version(model_id, version)
        fresh = self._get_model_version(model_id, model_version.version)
        return self._to_version_record(fresh, model_id)

    def get_version_by_id(self, model_id: str, version_id: str) -> VersionRecord:
        if "/" not in version_id:
            raise NotFoundError("Version not found", f"Unknown version id '{version_id}'.")
        expected_model, mlflow_version = version_id.split("/", 1)
        if expected_model != model_id:
            raise NotFoundError("Version not found", f"Version id '{version_id}' does not belong to '{model_id}'.")
        model_version = self._get_model_version(model_id, mlflow_version)
        return self._to_version_record(model_version, model_id)

    def promote_to_staging(self, model_id: str, version: str) -> VersionRecord:
        record = self.get_version(model_id, version)
        assert_can_promote_to_staging(stage=record.lifecycle_stage)
        self._apply_lifecycle(model_id, record.mlflow_version, LifecycleStage.STAGING)
        self._client.set_model_version_tag(
            model_id,
            record.mlflow_version,
            TAG_LOCK_VERSION,
            str(record.lock_version + 1),
        )
        logger.info("version_promoted_to_staging", model_id=model_id, version=version)
        return self.get_version(model_id, version)

    def transition_stage(self, model_id: str, version: str, target: LifecycleStage) -> VersionRecord:
        record = self.get_version(model_id, version)
        assert_can_promote(current=record.lifecycle_stage, target=target)
        self._apply_lifecycle(model_id, record.mlflow_version, target)
        self._client.set_model_version_tag(
            model_id,
            record.mlflow_version,
            TAG_LOCK_VERSION,
            str(record.lock_version + 1),
        )
        logger.info("version_stage_transitioned", model_id=model_id, version=version, stage=str(target))
        return self.get_version(model_id, version)

    def set_lifecycle_stage_after_deploy(self, model_id: str, version: str, target: LifecycleStage) -> VersionRecord:
        record = self.get_version(model_id, version)
        if record.lifecycle_stage == target:
            return record
        self._apply_lifecycle(model_id, record.mlflow_version, target)
        self._client.set_model_version_tag(
            model_id,
            record.mlflow_version,
            TAG_LOCK_VERSION,
            str(record.lock_version + 1),
        )
        return self.get_version(model_id, version)


_registry: MLflowRegistry | None = None


def get_model_registry() -> MLflowRegistry:
    global _registry
    if _registry is None:
        _registry = MLflowRegistry()
    return _registry


def set_model_registry(registry: MLflowRegistry | None) -> None:
    global _registry
    _registry = registry
