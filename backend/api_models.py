from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator


class HealthResponse(BaseModel):
    status: str


class DatabaseRequest(BaseModel):
    database_url: SecretStr
    schema_name: str = Field(default="public", min_length=1, max_length=63)
    baseline_path: str = Field(default="baseline.json", min_length=1)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        database_url = value.get_secret_value()
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("database_url must be a PostgreSQL URL")
        return value

    @field_validator("schema_name")
    @classmethod
    def validate_schema_name(cls, value: str) -> str:
        if not value.replace("_", "a").isalnum() or value[0].isdigit():
            raise ValueError("schema_name must contain letters, numbers, or underscores")
        return value

    @field_validator("baseline_path")
    @classmethod
    def validate_baseline_path(cls, value: str) -> str:
        if not value.lower().endswith(".json"):
            raise ValueError("baseline_path must end with .json")
        return value


class BaselineCaptureRequest(DatabaseRequest):
    pass


class AnalysisRequest(DatabaseRequest):
    project_path: str = Field(min_length=1)


class BaselineCaptureResponse(BaseModel):
    schema_name: str
    table_count: int
    column_count: int
    baseline_path: str


class AnalysisResponse(BaseModel):
    schema_name: str
    change_count: int
    processing_time_ms: float
    changes: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    warnings: list[dict[str, Any]]

