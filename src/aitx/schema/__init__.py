"""JSON Schema utilities — normalization, $ref resolution, strict mode."""

from .normalizer import normalize_schema
from .ref_resolver import inline_refs
from .strict_mode import ensure_strict_schema

__all__ = [
    "normalize_schema",
    "inline_refs",
    "ensure_strict_schema",
]
