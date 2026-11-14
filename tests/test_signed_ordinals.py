# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.

import os
os.environ.setdefault("OVRTX_SKIP_SCHEMA_AUTO_REGISTER", "1")

import numpy as np
import pytest
from ovrtx._src import bindings
from ovrtx import Renderer


@pytest.mark.parametrize("value", [
    bindings.OVSTAGE_ORDINAL_MIN, bindings.OVSTAGE_ORDINAL_MIN + 1,
    -1, 0, 1, bindings.OVSTAGE_ORDINAL_MAX,
])
def test_signed_stage_ordinal_roundtrip(value):
    normalized = Renderer._normalize_ordinal(np.int64(value))
    assert normalized == value
    assert bindings.ovstage_ordinal_t(normalized).value == value


@pytest.mark.parametrize("value", [bindings.OVSTAGE_ORDINAL_MIN - 1, bindings.OVSTAGE_ORDINAL_MAX + 1, (1 << 64) - 1])
def test_stage_ordinal_cannot_wrap(value):
    with pytest.raises(ValueError, match="int64"):
        Renderer._normalize_ordinal(value)


@pytest.mark.parametrize("value", [1.0, -0.5, "0", None])
def test_stage_ordinal_requires_integer(value):
    with pytest.raises(TypeError):
        Renderer._normalize_ordinal(value)
