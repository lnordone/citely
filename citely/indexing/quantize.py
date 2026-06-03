"""int8 scalar quantization (toggle: config.indexing.quantization).

Symmetric scalar quantization with a fixed global scale. The default embedding model
(``bge-base-en-v1.5``) produces L2-normalized vectors, so components lie in ``[-1, 1]``
and map cleanly onto the int8 range ``[-127, 127]`` with ``scale = 1/127``.

The on-disk form is a plain int8 byte string (no per-vector scale header), which keeps
the ``passages.embedding_i8`` column compact; callers reconstruct with the known
:data:`INT8_SCALE`.
"""

from __future__ import annotations

import numpy as np

# Maps the normalized range [-1, 1] onto the symmetric int8 range [-127, 127].
INT8_SCALE = 1.0 / 127.0


def quantize_int8(vector: list[float]) -> bytes:
    """Scalar-quantize a float vector to int8 bytes (clamped to [-127, 127])."""
    arr = np.asarray(vector, dtype=np.float32)
    q = np.clip(np.round(arr / INT8_SCALE), -127, 127).astype(np.int8)
    return q.tobytes()


def dequantize_int8(data: bytes, scale: float = INT8_SCALE) -> list[float]:
    """Inverse of :func:`quantize_int8`."""
    q = np.frombuffer(data, dtype=np.int8).astype(np.float32)
    return (q * scale).tolist()
