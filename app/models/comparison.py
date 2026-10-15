"""Validated contracts for the automatic research pipeline."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompareRequest(Contract):
    query: str = Field(min_length=5, max_length=600)
    country: str = Field(default="India", min_length=2, max_length=60)

    @field_validator("query", "country", mode="before")
    @classmethod
    def trim(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Enter text")
        value = value.strip()
        if not value:
            raise ValueError("Enter a comparison")
        return value


class Credentials(Contract):
    tavily: SecretStr
    openai: SecretStr


class ResearchPlan(Contract):
    products: list[str]
    focus: str
    assumptions: list[str]


class CitedText(Contract):
    text: str
    source_ids: list[str]


class Offer(Contract):
    price_text: str
    source_id: str


class ComparedProduct(Contract):
    id: str
    name: str
    variant_note: str
    best_for: CitedText
    strengths: list[CitedText]
    limitations: list[CitedText]
    offers: list[Offer]


class AttributeValue(Contract):
    product_id: str
    value: str
    source_ids: list[str]


class ComparisonRow(Contract):
    attribute: str
    values: list[AttributeValue]


class Recommendation(Contract):
    product_id: str | None
    verdict: str
    reason: str
    source_ids: list[str]


class ComparisonDraft(Contract):
    title: str
    products: list[ComparedProduct]
    rows: list[ComparisonRow]
    recommendation: Recommendation
    caveats: list[str]


class Source(Contract):
    id: str
    product_id: str
    title: str
    url: str
    excerpt: str
    retrieved_at: str
    kind: Literal["page", "search_excerpt"]
    image_urls: list[str] = []


class ComparisonResult(ComparisonDraft):
    query: str
    country: str
    assumptions: list[str]
    sources: list[Source]
    checked_at: str
    warnings: list[str]

