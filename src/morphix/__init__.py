"""Morphix — Verto's offline conversion engine.

Morphix handles all format detection and conversion work under the hood,
including PDF merge/split/compress and optional local OCR.
"""

from morphix.base import ConversionError, ConversionResult
from morphix.engine import MorphixEngine

__all__ = ["MorphixEngine", "ConversionResult", "ConversionError"]
