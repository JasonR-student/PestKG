from __future__ import annotations

from datetime import date
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class RegistrationUseFilters(BaseModel):
    jurisdictions: list[str] = Field(default_factory=list, max_length=12)
    query: str | None = Field(default=None, max_length=200)
    product: str | None = Field(default=None, max_length=200)
    active_ingredient: str | None = Field(default=None, max_length=200)
    crop: str | None = Field(default=None, max_length=200)
    target: str | None = Field(default=None, max_length=200)
    formulation: str | None = Field(default=None, max_length=200)
    registration_status: str | None = Field(default=None, max_length=100)
    pairing_status: str | None = Field(default=None, max_length=100)
    valid_on: date | None = None

    @field_validator("jurisdictions")
    @classmethod
    def normalize_jurisdictions(cls, values: list[str]) -> list[str]:
        return sorted({value.strip().upper() for value in values if value.strip()})


class RegistrationUseQuery(BaseModel):
    filters: RegistrationUseFilters = Field(default_factory=RegistrationUseFilters)
    cursor: str | None = None
    page_size: int = Field(default=50, ge=1, le=200)


class ExportRequest(BaseModel):
    filters: RegistrationUseFilters = Field(default_factory=RegistrationUseFilters)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class CoverageRecord(ContractModel):
    jurisdiction: str
    source_language: str
    records: str
    crop_source: str
    target_source: str
    active_source: str
    formulation_source: str
    crop_english: str
    target_english: str
    active_english: str
    formulation_english: str
    crop_english_given_source: str
    target_english_given_source: str
    active_english_given_source: str
    formulation_english_given_source: str


class OverviewData(ContractModel):
    title: str
    version: str
    published_at: str
    cutoff: str
    status: str
    distribution_status: str
    known_limitations: list[str]
    mode: str
    jurisdictions: int
    source_records: int
    country_nodes: int
    country_edges: int
    shared_nodes: int
    alignment_edges: int
    node_types: dict[str, int]
    relation_types: dict[str, int]
    coverage: list[CoverageRecord]


class CountryData(ContractModel):
    jurisdiction: str
    jurisdiction_name: str
    sovereign_country: str
    site_id: str
    official_url: str
    source_file: str
    source_sha256: str
    source_snapshot_eligible: bool
    source_rows: int
    skipped_rows: int
    nodes: int
    edges: int
    broken_edges: int
    graph_scope: str
    language: str
    iso3: str
    map_id: str
    coverage: CoverageRecord


class EntityRef(ContractModel):
    id: str
    label_original: str
    label_en: str | None


class EntityData(EntityRef):
    type: str
    jurisdiction: str
    source_record_id: str
    source_url: str
    properties: dict[str, Any]


class EdgeData(ContractModel):
    id: str
    start_id: str
    predicate: str
    end_id: str
    jurisdiction: str
    source_record_id: str
    source_url: str
    properties: dict[str, Any]


class GraphData(ContractModel):
    nodes: list[EntityData]
    edges: list[EdgeData]


class RegistrationUseData(ContractModel):
    use_id: str
    jurisdiction: str
    product_id: str
    product_label_original: str
    product_label_en: str | None
    active_ingredients: list[EntityRef]
    crops: list[EntityRef]
    targets: list[EntityRef]
    formulations: list[EntityRef]
    registration_status: str | None
    registration_date: str | None
    expiry_date: str | None
    pairing_status: str
    source_record_id: str
    source_url: str


class SchemaData(ContractModel):
    schema_version: str
    node_fields: list[str]
    edge_fields: list[str]
    node_types: dict[str, int]
    relation_types: dict[str, int]
    federation_predicates: dict[str, int]
    rules: dict[str, str]


class ComparisonRow(RootModel[dict[str, str | None]]):
    pass


class ReleaseArtifact(ContractModel):
    path: str
    url: str
    category: str
    format: str
    media_type: str
    bytes: int
    sha256: str


class ReleaseIntegrity(ContractModel):
    passed: bool
    checks: dict[str, bool]


class ReleaseData(ContractModel):
    release_id: str
    schema_version: str
    title: str
    published_at: str
    cutoff: str
    status: str
    distribution_status: str
    known_limitations: list[str]
    license: str
    inventory: dict[str, int]
    integrity: ReleaseIntegrity
    artifacts: list[ReleaseArtifact]
    is_active: bool
    registry_status: str
    registered_at: str | None


T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    api_version: str = "1.1"
    release_id: str
    schema_version: str = "1.0"
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, str] = Field(default_factory=dict)


class ErrorDescriptor(BaseModel):
    code: str
    message: str
    details: Any = Field(default_factory=dict)
    request_id: str


class ErrorEnvelope(BaseModel):
    detail: Any
    error: ErrorDescriptor
