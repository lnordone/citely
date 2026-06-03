"""int8 scalar quantization (toggle: config.indexing.quantization).

# TODO(phase 4): per-vector or global scale; pack to bytes; dequantize for scoring.
"""

from __future__ import annotations


def quantize_int8(vector: list[float]) -> bytes:
    """Scalar-quantize a float vector to int8 bytes."""
    raise NotImplementedError  # TODO(phase 4)


def dequantize_int8(data: bytes, scale: float) -> list[float]:
    """Inverse of :func:`quantize_int8`."""
    raise NotImplementedError  # TODO(phase 4)
