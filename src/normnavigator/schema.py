"""Core data model shared by ingestion, retrieval and evaluation.

Design decision: one chunk = one numbered paragraph of one article, in one language.
Why: legal answers are cited as "Art. 18(2)". If chunks follow the legal structure,
every retrieved chunk maps 1:1 to a citation a compliance engineer can check.
Fixed-size token windows (the usual RAG default) would cut paragraphs in half and
make citations fuzzy.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["de", "en"]


class Chunk(BaseModel):
    regulation: str = Field(description="Short regulation id, e.g. '2023/1230'")
    lang: Lang
    article: str = Field(description="Article number as printed, e.g. '18'")
    paragraph: str | None = Field(default=None, description="Paragraph number, e.g. '2'")
    title: str = Field(
        default="", description="Article heading, e.g. 'Obligations of manufacturers'"
    )
    text: str

    @property
    def chunk_id(self) -> str:
        """Unique id, e.g. '2023/1230:de:art18:p2'."""
        base = f"{self.regulation}:{self.lang}:art{self.article}"
        return f"{base}:p{self.paragraph}" if self.paragraph else base

    @property
    def article_key(self) -> str:
        """Language-independent article id used for gold labels, e.g. '2023/1230:art18'."""
        return f"{self.regulation}:art{self.article}"


def article_key_from_chunk_id(chunk_id: str) -> str:
    """'2023/1230:de:art18:p2' -> '2023/1230:art18'.

    Gold labels are per article and language-independent, so a German question that
    retrieves the English version of the right article still counts as a hit. That is
    exactly the cross-lingual ability we want to measure.
    """
    parts = chunk_id.split(":")
    if len(parts) < 3 or not parts[2].startswith("art"):
        raise ValueError(f"Malformed chunk id: {chunk_id!r}")
    return f"{parts[0]}:{parts[2]}"
