"""Shared contracts; no dependency on workflow or infrastructure."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonNegativeInt = Annotated[int, Field(ge=0, strict=True)]
Ratio = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EvidenceRef(Contract):
    source_id: NonEmptyText
    quote: NonEmptyText
    locator: NonEmptyText
