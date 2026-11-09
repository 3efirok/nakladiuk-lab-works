"""Pydantic v2 schemas: request bodies, responses and validation rules."""

import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Parameter = Annotated[str, Field(min_length=1, max_length=50, pattern=r"^[a-z_]+$", examples=["temperature"])]
Result = Annotated[float, Field(ge=0, le=1_000_000, allow_inf_nan=False, examples=[293.4])]
SortOrder = Literal["date", "-date", "result", "-result"]


def _not_in_future(value: dt.date | None) -> dt.date | None:
    if value is not None and value > dt.date.today():
        raise ValueError("date cannot be in the future")
    return value


class ResearcherCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120, examples=["Olena Kovalenko"])
    email: str | None = Field(
        default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", examples=["o.kovalenko@lnu.edu.ua"]
    )
    department: str = Field(default="Physics", max_length=80)


class ResearcherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str | None
    department: str


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Thermal conductivity of Al alloy"])
    researcher_id: int = Field(gt=0, examples=[1])
    parameter: Parameter
    result: Result
    date: dt.date
    notes: str | None = Field(default=None, max_length=500)

    _check_date = field_validator("date")(_not_in_future)


class ExperimentUpdate(BaseModel):
    """PATCH body: every field is optional, only the sent fields are changed."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    parameter: Parameter | None = None
    result: Result | None = None
    date: dt.date | None = None  # module alias: a field named `date` would shadow the type
    notes: str | None = Field(default=None, max_length=500)

    _check_date = field_validator("date")(_not_in_future)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ExperimentUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    researcher_id: int
    researcher: str
    parameter: str
    result: float
    date: dt.date
    notes: str | None

    @field_validator("researcher", mode="before")
    @classmethod
    def researcher_name(cls, value: object) -> object:
        return getattr(value, "full_name", value)


class StatisticsRead(BaseModel):
    count: int
    average: float | None
    minimum: float | None
    maximum: float | None
    parameter: str | None = None
    researcher_id: int | None = None


class ExtendedStatisticsRead(BaseModel):
    """NumPy-based statistics with caching (lab 9 optimization)."""

    model_config = ConfigDict(from_attributes=True)

    count: int
    mean: float | None
    std: float | None
    minimum: float | None
    maximum: float | None
    median: float | None
    p95: float | None
    parameter: str | None
    version: int
    cached: bool = False


class ResearcherStatistics(BaseModel):
    researcher_id: int
    statistics: StatisticsRead | None = None
    error: str | None = None


class AggregatedStatistics(BaseModel):
    items: list[ResearcherStatistics]
    elapsed_ms: float
    max_concurrency: int


class ErrorResponse(BaseModel):
    detail: str
