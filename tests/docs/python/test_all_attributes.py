# Copyright (c) 2026, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Round-trip coverage for supported authored USD attribute types."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import ovrtx
import ovstage
import pytest
from ovrtx._src import bindings


ALL_ATTRIBUTES_PATH = str((Path(__file__).parent / "../data/all-attributes.usda").resolve())
WORLD = "/World"
EXTENT_LEAF = "/World/ExtentTranslate/ExtentScale/ExtentLeaf"

pytestmark = pytest.mark.filterwarnings("ignore:.* is deprecated in ovrtx 0\\.4\\..*:DeprecationWarning")


@dataclass(frozen=True)
class AttributeCase:
    usd_type: str
    name: str
    initial: Any
    updated: Any
    dtype: np.dtype | None = None
    value_shape: tuple[int, ...] = ()
    is_array: bool = False
    kind: Literal["numeric", "token", "token_array", "asset", "string"] = "numeric"


def _load_all_attributes(renderer):
    renderer.open_usd(ALL_ATTRIBUTES_PATH)
    renderer.reset()


def _updated_numeric(value: Any, dtype: np.dtype) -> Any:
    arr = np.array(value, dtype=dtype)
    if arr.dtype == np.bool_:
        return np.logical_not(arr).tolist()
    if np.issubdtype(arr.dtype, np.integer):
        return (arr + np.array(7, dtype=arr.dtype)).tolist()
    return (arr + np.array(0.75, dtype=arr.dtype)).tolist()


def _numeric_case(
    usd_type: str,
    suffix: str,
    dtype: np.dtype,
    initial: Any,
    value_shape: tuple[int, ...] = (),
    is_array: bool = False,
) -> AttributeCase:
    return AttributeCase(
        usd_type=usd_type,
        name=f"test:{suffix}",
        initial=initial,
        updated=_updated_numeric(initial, dtype),
        dtype=np.dtype(dtype),
        value_shape=value_shape,
        is_array=is_array,
    )


def _flat(*rows: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(component for row in rows for component in row)


def _runtime_quat(real: float, i: float, j: float, k: float) -> tuple[float, float, float, float]:
    return (i, j, k, real)


SUPPORTED_ATTRIBUTE_CASES = [
    AttributeCase("asset", "test:asset", "initial_asset.usd", "updated_asset.usd", kind="asset"),
    _numeric_case("bool", "bool", np.bool_, True),
    _numeric_case("bool[]", "boolArray", np.bool_, [True, False], is_array=True),
    _numeric_case("color3d", "color3d", np.float64, (1.1, 1.2, 1.3), (3,)),
    _numeric_case("color3d[]", "color3dArray", np.float64, [(1.1, 1.2, 1.3), (2.1, 2.2, 2.3)], (3,), True),
    _numeric_case("color3f", "color3f", np.float32, (3.1, 3.2, 3.3), (3,)),
    _numeric_case("color3f[]", "color3fArray", np.float32, [(3.1, 3.2, 3.3), (4.1, 4.2, 4.3)], (3,), True),
    _numeric_case("color3h", "color3h", np.float16, (5.0, 5.5, 6.0), (3,)),
    _numeric_case("color3h[]", "color3hArray", np.float16, [(5.0, 5.5, 6.0), (6.5, 7.0, 7.5)], (3,), True),
    _numeric_case("color4d", "color4d", np.float64, (7.1, 7.2, 7.3, 7.4), (4,)),
    _numeric_case(
        "color4d[]",
        "color4dArray",
        np.float64,
        [(7.1, 7.2, 7.3, 7.4), (8.1, 8.2, 8.3, 8.4)],
        (4,),
        True,
    ),
    _numeric_case("color4f", "color4f", np.float32, (9.1, 9.2, 9.3, 9.4), (4,)),
    _numeric_case(
        "color4f[]",
        "color4fArray",
        np.float32,
        [(9.1, 9.2, 9.3, 9.4), (10.1, 10.2, 10.3, 10.4)],
        (4,),
        True,
    ),
    _numeric_case("color4h", "color4h", np.float16, (11.0, 11.5, 12.0, 12.5), (4,)),
    _numeric_case(
        "color4h[]",
        "color4hArray",
        np.float16,
        [(11.0, 11.5, 12.0, 12.5), (13.0, 13.5, 14.0, 14.5)],
        (4,),
        True,
    ),
    _numeric_case("double", "double", np.float64, 15.25),
    _numeric_case("double2", "double2", np.float64, (16.1, 16.2), (2,)),
    _numeric_case("double2[]", "double2Array", np.float64, [(16.1, 16.2), (17.1, 17.2)], (2,), True),
    _numeric_case("double3", "double3", np.float64, (18.1, 18.2, 18.3), (3,)),
    _numeric_case("double3[]", "double3Array", np.float64, [(18.1, 18.2, 18.3), (19.1, 19.2, 19.3)], (3,), True),
    _numeric_case("double4", "double4", np.float64, (20.1, 20.2, 20.3, 20.4), (4,)),
    _numeric_case(
        "double4[]",
        "double4Array",
        np.float64,
        [(20.1, 20.2, 20.3, 20.4), (21.1, 21.2, 21.3, 21.4)],
        (4,),
        True,
    ),
    _numeric_case("double[]", "doubleArray", np.float64, [22.1, 22.2], is_array=True),
    _numeric_case("float", "float", np.float32, 23.5),
    _numeric_case("float2", "float2", np.float32, (24.1, 24.2), (2,)),
    _numeric_case("float2[]", "float2Array", np.float32, [(24.1, 24.2), (25.1, 25.2)], (2,), True),
    _numeric_case("float3", "float3", np.float32, (26.1, 26.2, 26.3), (3,)),
    _numeric_case("float3[]", "float3Array", np.float32, [(26.1, 26.2, 26.3), (27.1, 27.2, 27.3)], (3,), True),
    _numeric_case("float4", "float4", np.float32, (28.1, 28.2, 28.3, 28.4), (4,)),
    _numeric_case(
        "float4[]",
        "float4Array",
        np.float32,
        [(28.1, 28.2, 28.3, 28.4), (29.1, 29.2, 29.3, 29.4)],
        (4,),
        True,
    ),
    _numeric_case("float[]", "floatArray", np.float32, [30.1, 30.2], is_array=True),
    _numeric_case(
        "frame4d",
        "frame4d",
        np.float64,
        _flat((1, 0, 0, 0), (0, 2, 0, 0), (0, 0, 3, 0), (4, 5, 6, 1)),
        (16,),
    ),
    _numeric_case(
        "frame4d[]",
        "frame4dArray",
        np.float64,
        [
            _flat((1, 0, 0, 0), (0, 2, 0, 0), (0, 0, 3, 0), (4, 5, 6, 1)),
            _flat((2, 0, 0, 0), (0, 3, 0, 0), (0, 0, 4, 0), (5, 6, 7, 1)),
        ],
        (16,),
        True,
    ),
    _numeric_case("half", "half", np.float16, 31.5),
    _numeric_case("half2", "half2", np.float16, (32.0, 32.5), (2,)),
    _numeric_case("half2[]", "half2Array", np.float16, [(32.0, 32.5), (33.0, 33.5)], (2,), True),
    _numeric_case("half3", "half3", np.float16, (34.0, 34.5, 35.0), (3,)),
    _numeric_case("half3[]", "half3Array", np.float16, [(34.0, 34.5, 35.0), (35.5, 36.0, 36.5)], (3,), True),
    _numeric_case("half4", "half4", np.float16, (37.0, 37.5, 38.0, 38.5), (4,)),
    _numeric_case(
        "half4[]",
        "half4Array",
        np.float16,
        [(37.0, 37.5, 38.0, 38.5), (39.0, 39.5, 40.0, 40.5)],
        (4,),
        True,
    ),
    _numeric_case("half[]", "halfArray", np.float16, [41.0, 41.5], is_array=True),
    _numeric_case("int", "int", np.int32, -42),
    _numeric_case("int2", "int2", np.int32, (-43, 44), (2,)),
    _numeric_case("int2[]", "int2Array", np.int32, [(-43, 44), (45, -46)], (2,), True),
    _numeric_case("int3", "int3", np.int32, (-47, 48, -49), (3,)),
    _numeric_case("int3[]", "int3Array", np.int32, [(-47, 48, -49), (50, -51, 52)], (3,), True),
    _numeric_case("int4", "int4", np.int32, (-53, 54, -55, 56), (4,)),
    _numeric_case("int4[]", "int4Array", np.int32, [(-53, 54, -55, 56), (57, -58, 59, -60)], (4,), True),
    _numeric_case("int64", "int64", np.int64, -6100000000),
    _numeric_case("int64[]", "int64Array", np.int64, [-6200000000, 6300000000], is_array=True),
    _numeric_case("int[]", "intArray", np.int32, [-64, 65], is_array=True),
    _numeric_case("matrix2d", "matrix2d", np.float64, _flat((1, 2), (3, 4)), (4,)),
    _numeric_case("matrix2d[]", "matrix2dArray", np.float64, [_flat((1, 2), (3, 4)), _flat((5, 6), (7, 8))], (4,), True),
    _numeric_case("matrix3d", "matrix3d", np.float64, _flat((1, 2, 3), (4, 5, 6), (7, 8, 9)), (9,)),
    _numeric_case(
        "matrix3d[]",
        "matrix3dArray",
        np.float64,
        [_flat((1, 2, 3), (4, 5, 6), (7, 8, 9)), _flat((10, 11, 12), (13, 14, 15), (16, 17, 18))],
        (9,),
        True,
    ),
    _numeric_case(
        "matrix4d",
        "matrix4d",
        np.float64,
        _flat((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16)),
        (16,),
    ),
    _numeric_case(
        "matrix4d[]",
        "matrix4dArray",
        np.float64,
        [
            _flat((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16)),
            _flat((17, 18, 19, 20), (21, 22, 23, 24), (25, 26, 27, 28), (29, 30, 31, 32)),
        ],
        (16,),
        True,
    ),
    _numeric_case("normal3d", "normal3d", np.float64, (66.1, 66.2, 66.3), (3,)),
    _numeric_case("normal3d[]", "normal3dArray", np.float64, [(66.1, 66.2, 66.3), (67.1, 67.2, 67.3)], (3,), True),
    _numeric_case("normal3f", "normal3f", np.float32, (68.1, 68.2, 68.3), (3,)),
    _numeric_case("normal3f[]", "normal3fArray", np.float32, [(68.1, 68.2, 68.3), (69.1, 69.2, 69.3)], (3,), True),
    _numeric_case("normal3h", "normal3h", np.float16, (70.0, 70.5, 71.0), (3,)),
    _numeric_case("normal3h[]", "normal3hArray", np.float16, [(70.0, 70.5, 71.0), (71.5, 72.0, 72.5)], (3,), True),
    _numeric_case("point3d", "point3d", np.float64, (73.1, 73.2, 73.3), (3,)),
    _numeric_case("point3d[]", "point3dArray", np.float64, [(73.1, 73.2, 73.3), (74.1, 74.2, 74.3)], (3,), True),
    _numeric_case("point3f", "point3f", np.float32, (75.1, 75.2, 75.3), (3,)),
    _numeric_case("point3f[]", "point3fArray", np.float32, [(75.1, 75.2, 75.3), (76.1, 76.2, 76.3)], (3,), True),
    _numeric_case("point3h", "point3h", np.float16, (77.0, 77.5, 78.0), (3,)),
    _numeric_case("point3h[]", "point3hArray", np.float16, [(77.0, 77.5, 78.0), (78.5, 79.0, 79.5)], (3,), True),
    _numeric_case("quatd", "quatd", np.float64, _runtime_quat(1, 80.1, 80.2, 80.3), (4,)),
    _numeric_case(
        "quatd[]",
        "quatdArray",
        np.float64,
        [_runtime_quat(1, 80.1, 80.2, 80.3), _runtime_quat(1, 81.1, 81.2, 81.3)],
        (4,),
        True,
    ),
    _numeric_case("quatf", "quatf", np.float32, _runtime_quat(1, 82.1, 82.2, 82.3), (4,)),
    _numeric_case(
        "quatf[]",
        "quatfArray",
        np.float32,
        [_runtime_quat(1, 82.1, 82.2, 82.3), _runtime_quat(1, 83.1, 83.2, 83.3)],
        (4,),
        True,
    ),
    _numeric_case("quath", "quath", np.float16, _runtime_quat(1, 84.0, 84.5, 85.0), (4,)),
    _numeric_case(
        "quath[]",
        "quathArray",
        np.float16,
        [_runtime_quat(1, 84.0, 84.5, 85.0), _runtime_quat(1, 85.5, 86.0, 86.5)],
        (4,),
        True,
    ),
    AttributeCase("string", "test:string", "initial string", "updated longer string", is_array=True, kind="string"),
    _numeric_case("texCoord2f", "texCoord2f", np.float32, (87.1, 87.2), (2,)),
    _numeric_case("texCoord2f[]", "texCoord2fArray", np.float32, [(87.1, 87.2), (88.1, 88.2)], (2,), True),
    AttributeCase("token", "test:token", "initialToken", "updatedToken", kind="token"),
    AttributeCase(
        "token[]",
        "test:tokenArray",
        ["initialTokenA", "initialTokenB"],
        ["updatedTokenA", "updatedTokenB"],
        is_array=True,
        kind="token_array",
    ),
    _numeric_case("uchar", "uchar", np.uint8, 91),
    _numeric_case("uchar[]", "ucharArray", np.uint8, [92, 93], is_array=True),
    _numeric_case("uint", "uint", np.uint32, 94),
    _numeric_case("uint64", "uint64", np.uint64, 9500000000),
    _numeric_case("uint64[]", "uint64Array", np.uint64, [9600000000, 9700000000], is_array=True),
    _numeric_case("uint[]", "uintArray", np.uint32, [98, 99], is_array=True),
    _numeric_case("vector3d", "vector3d", np.float64, (100.1, 100.2, 100.3), (3,)),
    _numeric_case("vector3d[]", "vector3dArray", np.float64, [(100.1, 100.2, 100.3), (101.1, 101.2, 101.3)], (3,), True),
    _numeric_case("vector3f", "vector3f", np.float32, (102.1, 102.2, 102.3), (3,)),
    _numeric_case("vector3f[]", "vector3fArray", np.float32, [(102.1, 102.2, 102.3), (103.1, 103.2, 103.3)], (3,), True),
    _numeric_case("vector3h", "vector3h", np.float16, (104.0, 104.5, 105.0), (3,)),
    _numeric_case("vector3h[]", "vector3hArray", np.float16, [(104.0, 104.5, 105.0), (105.5, 106.0, 106.5)], (3,), True),
]


KNOWN_USD_POPULATION_BUGS = {
    "test:float3": "scalar float3 is created but populated as zero; direct runtime write/read still works",
}


UNSUPPORTED_AUTHORED_ATTRIBUTE_NAMES = [
    "test:assetArray",
    "test:rel",
    "test:relArray",
    "test:stringArray",
    "test:timecode",
    "test:timecodeArray",
]


CASE_BY_NAME = {case.name: case for case in SUPPORTED_ATTRIBUTE_CASES}


def _attribute_info(renderer, name: str):
    prims = renderer.query_prims(
        require_all=[(ovrtx.FilterKind.HAS_ATTRIBUTE, name)],
        attribute_filter_mode=ovrtx.AttributeFilterMode.SPECIFIC,
        attribute_names=[name],
    )
    assert WORLD in prims, f"{name} was not populated on {WORLD}"
    assert name in prims[WORLD], f"{name} was not returned in query results for {WORLD}"
    return prims[WORLD][name]


def _numeric_expected(case: AttributeCase, value: Any) -> np.ndarray:
    assert case.dtype is not None
    arr = np.array(value, dtype=case.dtype)
    if case.is_array:
        return arr.reshape((-1, *case.value_shape))
    return arr.reshape((1, *case.value_shape))


def _read_numeric(renderer, case: AttributeCase) -> np.ndarray:
    if case.is_array:
        tensor = renderer.read_array_attribute(case.name, [WORLD])[WORLD]
    else:
        tensor = renderer.read_attribute(case.name, [WORLD])
    return np.array(np.from_dlpack(tensor))


def _write_numeric(renderer, case: AttributeCase) -> None:
    value = _numeric_expected(case, case.updated)
    if case.is_array:
        renderer.write_array_attribute([WORLD], case.name, [value])
    else:
        renderer.write_attribute([WORLD], case.name, value)


def _assert_array_close(label: str, actual: np.ndarray, expected: np.ndarray) -> None:
    assert actual.shape == expected.shape, f"{label} shape {actual.shape} != {expected.shape}"
    if np.issubdtype(expected.dtype, np.floating):
        atol = 1e-3 if expected.dtype == np.float16 else 1e-5
        rtol = 1e-3 if expected.dtype == np.float16 else 1e-5
        if not np.allclose(actual, expected, rtol=rtol, atol=atol):
            raise AssertionError(f"{label} value {actual.tolist()} != {expected.tolist()}")
    elif not np.array_equal(actual, expected):
        raise AssertionError(f"{label} value {actual.tolist()} != {expected.tolist()}")


def _path_dictionary(renderer):
    return renderer._get_path_dict()


def _create_token(renderer, text: str) -> int:
    pd = _path_dictionary(renderer)
    source = bindings.ovx_string_t(text)
    token = ctypes.c_uint64(0)
    result = pd.vtable.contents.create_tokens_from_strings(
        pd.context, ctypes.byref(source), 1, ctypes.byref(token)
    )
    assert result.status == 0, f"Failed to create token for {text!r}"
    return token.value


def _read_token_strings(renderer, case: AttributeCase) -> list[str]:
    pd = _path_dictionary(renderer)
    if case.is_array:
        tensor = renderer.read_array_attribute(case.name, [WORLD])[WORLD]
    else:
        tensor = renderer.read_attribute(case.name, [WORLD])
    values = np.array(np.from_dlpack(tensor))
    expected_shape = (len(case.initial),) if case.is_array else (1,)
    assert values.shape == expected_shape, f"token read shape {values.shape} != {expected_shape}"
    return [pd.token_to_string(int(value)) for value in values.reshape(-1)]


def _read_asset_string(renderer, case: AttributeCase) -> str:
    pd = _path_dictionary(renderer)
    values = np.array(np.from_dlpack(renderer.read_attribute(case.name, [WORLD])))
    assert values.shape == (1, 2), f"asset read shape {values.shape} != (1, 2)"
    assert int(values[0, 1]) == 0, f"asset second lane {int(values[0, 1])} != 0"
    return pd.token_to_string(int(values[0, 0]))


def _asset_tensor(renderer, value: str) -> np.ndarray:
    return np.array([[_create_token(renderer, value), 0]], dtype=np.uint64)


def _string_bytes(value: str) -> np.ndarray:
    return np.frombuffer(value.encode("utf-8"), dtype=np.uint8).copy()


def _read_string(renderer, case: AttributeCase, expected: str | None = None) -> str:
    values = np.array(np.from_dlpack(renderer.read_array_attribute(case.name, [WORLD])[WORLD]))
    expected_text = case.initial if expected is None else expected
    expected_shape = (len(expected_text.encode("utf-8")),)
    assert values.shape == expected_shape, f"string read shape {values.shape} != {expected_shape}"
    return bytes(values.tolist()).decode("utf-8")


def _check_case(renderer, case: AttributeCase) -> None:
    info = _attribute_info(renderer, case.name)
    assert info.is_array == case.is_array, f"is_array {info.is_array} != {case.is_array}"

    if case.kind == "numeric":
        if case.name not in KNOWN_USD_POPULATION_BUGS:
            _assert_array_close(
                f"{case.name} initial",
                _read_numeric(renderer, case),
                _numeric_expected(case, case.initial),
            )
        _write_numeric(renderer, case)
        _assert_array_close(f"{case.name} updated", _read_numeric(renderer, case), _numeric_expected(case, case.updated))
    elif case.kind == "token":
        assert _read_token_strings(renderer, case) == [case.initial]
        renderer.write_attribute([WORLD], case.name, [case.updated])
        assert _read_token_strings(renderer, case) == [case.updated]
    elif case.kind == "token_array":
        assert _read_token_strings(renderer, case) == case.initial
        renderer.write_array_attribute([WORLD], case.name, [case.updated], is_token=True)
        assert _read_token_strings(renderer, case) == case.updated
    elif case.kind == "asset":
        assert _read_asset_string(renderer, case) == case.initial
        renderer.write_attribute([WORLD], case.name, _asset_tensor(renderer, case.updated))
        assert _read_asset_string(renderer, case) == case.updated
    elif case.kind == "string":
        assert _read_string(renderer, case) == case.initial
        renderer.write_array_attribute([WORLD], case.name, [_string_bytes(case.updated)])
        assert _read_string(renderer, case, case.updated) == case.updated


def test_supported_authored_attributes_round_trip(renderer):
    """Read every supported authored type, write a new value, then read it back."""
    _load_all_attributes(renderer)

    successes = []
    failures = []

    for case in SUPPORTED_ATTRIBUTE_CASES:
        if case.name in KNOWN_USD_POPULATION_BUGS:
            continue
        try:
            _check_case(renderer, case)
        except Exception as exc:
            failures.append(f"{case.usd_type} {case.name}: {type(exc).__name__}: {exc}")
        else:
            successes.append(f"{case.usd_type} {case.name}")

    print("\nSupported authored attribute round-trip results:")
    print(f"  succeeded: {len(successes)}")
    for success in successes:
        print(f"    {success}")
    print(f"  failed: {len(failures)}")
    for failure in failures:
        print(f"    {failure}")

    assert not failures, "Supported authored attribute round-trip failures:\n" + "\n".join(failures)


def test_scalar_float3_population_bug_is_explicit(renderer):
    """Current runtime bug: authored scalar float3 populates as zero, but runtime writes work."""
    _load_all_attributes(renderer)

    case = CASE_BY_NAME["test:float3"]
    initial = _read_numeric(renderer, case)
    assert initial.shape == (1, 3)
    _assert_array_close("test:float3 populated bug value", initial, np.zeros((1, 3), dtype=np.float32))

    _write_numeric(renderer, case)
    _assert_array_close("test:float3 updated", _read_numeric(renderer, case), _numeric_expected(case, case.updated))


def test_unsupported_authored_attributes_are_not_populated(renderer):
    """Documented unsupported authored fields remain absent from runtime attribute queries."""
    _load_all_attributes(renderer)

    prims = renderer.query_prims(attribute_filter_mode=ovrtx.AttributeFilterMode.ALL)
    world_attributes = prims[WORLD]
    unexpected = [name for name in UNSUPPORTED_AUTHORED_ATTRIBUTE_NAMES if name in world_attributes]
    assert not unexpected, f"Unsupported authored attributes were populated unexpectedly: {unexpected}"


def test_raw_attribute_read_write_snippets(renderer):
    """Raw snippets for docs/skills: direct ovrtx calls only, assertions outside."""
    _load_all_attributes(renderer)

    bool_values = np.array(np.from_dlpack(renderer.read_attribute("test:bool", [WORLD])))
    assert bool_values.shape == (1,)

    renderer.write_attribute([WORLD], "test:bool", np.array([False], dtype=np.bool_))
    _assert_array_close("test:bool", _read_numeric(renderer, CASE_BY_NAME["test:bool"]), np.array([False]))

    # [snippet:doc-read-usd-int]
    int_values = np.array(np.from_dlpack(renderer.read_attribute("test:int", [WORLD])))
    # [/snippet:doc-read-usd-int]
    assert int_values.shape == (1,)

    # [snippet:doc-write-usd-int]
    renderer.write_attribute([WORLD], "test:int", np.array([-35], dtype=np.int32))
    # [/snippet:doc-write-usd-int]
    _assert_array_close("test:int", _read_numeric(renderer, CASE_BY_NAME["test:int"]), np.array([-35], dtype=np.int32))

    # [snippet:doc-read-usd-float]
    float_values = np.array(np.from_dlpack(renderer.read_attribute("test:float", [WORLD])))
    # [/snippet:doc-read-usd-float]
    assert float_values.shape == (1,)

    # [snippet:doc-write-usd-float]
    renderer.write_attribute([WORLD], "test:float", np.array([24.25], dtype=np.float32))
    # [/snippet:doc-write-usd-float]
    _assert_array_close("test:float", _read_numeric(renderer, CASE_BY_NAME["test:float"]), np.array([24.25], dtype=np.float32))

    # [snippet:doc-read-usd-point3f]
    point3f_values = np.array(np.from_dlpack(renderer.read_attribute("test:point3f", [WORLD])))
    # [/snippet:doc-read-usd-point3f]
    assert point3f_values.shape == (1, 3)

    # [snippet:doc-write-usd-point3f]
    renderer.write_attribute([WORLD], "test:point3f", np.array([[75.85, 75.95, 76.05]], dtype=np.float32))
    # [/snippet:doc-write-usd-point3f]
    _assert_array_close(
        "test:point3f",
        _read_numeric(renderer, CASE_BY_NAME["test:point3f"]),
        np.array([[75.85, 75.95, 76.05]], dtype=np.float32),
    )

    # [snippet:doc-read-usd-point3f-array]
    point3f_array_values = np.array(np.from_dlpack(renderer.read_array_attribute("test:point3fArray", [WORLD])[WORLD]))
    # [/snippet:doc-read-usd-point3f-array]
    assert point3f_array_values.shape == (2, 3)

    # [snippet:doc-write-usd-point3f-array]
    renderer.write_array_attribute(
        [WORLD],
        "test:point3fArray",
        [np.array([[75.85, 75.95, 76.05], [76.85, 76.95, 77.05]], dtype=np.float32)],
    )
    # [/snippet:doc-write-usd-point3f-array]
    _assert_array_close(
        "test:point3fArray",
        _read_numeric(renderer, CASE_BY_NAME["test:point3fArray"]),
        np.array([[75.85, 75.95, 76.05], [76.85, 76.95, 77.05]], dtype=np.float32),
    )

    # [snippet:doc-read-usd-normal3f]
    normal3f_values = np.array(np.from_dlpack(renderer.read_attribute("test:normal3f", [WORLD])))
    # [/snippet:doc-read-usd-normal3f]
    assert normal3f_values.shape == (1, 3)

    # [snippet:doc-write-usd-normal3f]
    renderer.write_attribute([WORLD], "test:normal3f", np.array([[68.85, 68.95, 69.05]], dtype=np.float32))
    # [/snippet:doc-write-usd-normal3f]
    _assert_array_close(
        "test:normal3f",
        _read_numeric(renderer, CASE_BY_NAME["test:normal3f"]),
        np.array([[68.85, 68.95, 69.05]], dtype=np.float32),
    )

    # [snippet:doc-read-usd-vector3f]
    vector3f_values = np.array(np.from_dlpack(renderer.read_attribute("test:vector3f", [WORLD])))
    # [/snippet:doc-read-usd-vector3f]
    assert vector3f_values.shape == (1, 3)

    # [snippet:doc-write-usd-vector3f]
    renderer.write_attribute([WORLD], "test:vector3f", np.array([[102.85, 102.95, 103.05]], dtype=np.float32))
    # [/snippet:doc-write-usd-vector3f]
    _assert_array_close(
        "test:vector3f",
        _read_numeric(renderer, CASE_BY_NAME["test:vector3f"]),
        np.array([[102.85, 102.95, 103.05]], dtype=np.float32),
    )

    # [snippet:doc-read-usd-color3f]
    color3f_values = np.array(np.from_dlpack(renderer.read_attribute("test:color3f", [WORLD])))
    # [/snippet:doc-read-usd-color3f]
    assert color3f_values.shape == (1, 3)

    # [snippet:doc-write-usd-color3f]
    renderer.write_attribute([WORLD], "test:color3f", np.array([[3.85, 3.95, 4.05]], dtype=np.float32))
    # [/snippet:doc-write-usd-color3f]
    _assert_array_close(
        "test:color3f",
        _read_numeric(renderer, CASE_BY_NAME["test:color3f"]),
        np.array([[3.85, 3.95, 4.05]], dtype=np.float32),
    )

    # [snippet:doc-read-usd-matrix4d]
    matrix4d_values = np.array(np.from_dlpack(renderer.read_attribute("test:matrix4d", [WORLD])))
    # [/snippet:doc-read-usd-matrix4d]
    assert matrix4d_values.shape == (1, 16)

    # [snippet:doc-write-usd-matrix4d]
    renderer.write_attribute(
        [WORLD],
        "test:matrix4d",
        np.array([[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]], dtype=np.float64),
    )
    # [/snippet:doc-write-usd-matrix4d]
    _assert_array_close(
        "test:matrix4d",
        _read_numeric(renderer, CASE_BY_NAME["test:matrix4d"]),
        np.array([[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]], dtype=np.float64),
    )

    # [snippet:doc-read-usd-quatf]
    quatf_values = np.array(np.from_dlpack(renderer.read_attribute("test:quatf", [WORLD])))
    # [/snippet:doc-read-usd-quatf]
    assert quatf_values.shape == (1, 4)

    # [snippet:doc-write-usd-quatf]
    renderer.write_attribute([WORLD], "test:quatf", np.array([[82.85, 82.95, 83.05, 1.75]], dtype=np.float32))
    # [/snippet:doc-write-usd-quatf]
    _assert_array_close(
        "test:quatf",
        _read_numeric(renderer, CASE_BY_NAME["test:quatf"]),
        np.array([[82.85, 82.95, 83.05, 1.75]], dtype=np.float32),
    )

    # [snippet:doc-read-usd-string]
    string_bytes = np.array(np.from_dlpack(renderer.read_array_attribute("test:string", [WORLD])[WORLD]))
    string_value = bytes(string_bytes.tolist()).decode("utf-8")
    # [/snippet:doc-read-usd-string]
    assert string_value == "initial string"

    # [snippet:doc-write-usd-string]
    renderer.write_array_attribute(
        [WORLD],
        "test:string",
        [np.frombuffer("updated longer string".encode("utf-8"), dtype=np.uint8).copy()],
    )
    # [/snippet:doc-write-usd-string]
    assert _read_string(renderer, CASE_BY_NAME["test:string"], "updated longer string") == "updated longer string"

    token_ids = np.array(np.from_dlpack(renderer.read_attribute("test:token", [WORLD])))
    token_value = _path_dictionary(renderer).token_to_string(int(token_ids[0]))
    assert token_value == "initialToken"

    # [snippet:doc-write-usd-token]
    renderer.write_attribute([WORLD], "test:token", ["updatedToken"])
    # [/snippet:doc-write-usd-token]
    assert _read_token_strings(renderer, CASE_BY_NAME["test:token"]) == ["updatedToken"]

    token_array_ids = np.array(np.from_dlpack(renderer.read_array_attribute("test:tokenArray", [WORLD])[WORLD]))
    token_array_values = [_path_dictionary(renderer).token_to_string(int(token_id)) for token_id in token_array_ids]
    assert token_array_values == ["initialTokenA", "initialTokenB"]

    # [snippet:doc-write-usd-token-array]
    renderer.write_array_attribute([WORLD], "test:tokenArray", [["updatedTokenA", "updatedTokenB"]], is_token=True)
    # [/snippet:doc-write-usd-token-array]
    assert _read_token_strings(renderer, CASE_BY_NAME["test:tokenArray"]) == ["updatedTokenA", "updatedTokenB"]

    asset_values = np.array(np.from_dlpack(renderer.read_attribute("test:asset", [WORLD])))
    asset_value = _path_dictionary(renderer).token_to_string(int(asset_values[0, 0]))
    assert asset_value == "initial_asset.usd"

    asset_pd = renderer._get_path_dict()
    asset_source = bindings.ovx_string_t("updated_asset.usd")
    asset_token = ctypes.c_uint64(0)
    asset_pd.vtable.contents.create_tokens_from_strings(
        asset_pd.context, ctypes.byref(asset_source), 1, ctypes.byref(asset_token)
    )
    renderer.write_attribute([WORLD], "test:asset", np.array([[asset_token.value, 0]], dtype=np.uint64))
    assert _read_asset_string(renderer, CASE_BY_NAME["test:asset"]) == "updated_asset.usd"


def test_ovstage_bool_read_write_snippets(stage):
    """Representative ovstage scalar read/write snippets for authored attributes."""
    ovstage.population.open_usd(stage, ALL_ATTRIBUTES_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings([WORLD])
        with stage.query_from_path_list(path_list) as query:
            attribute = paths.intern_token("test:bool")

            # [snippet:doc-read-usd-bool]
            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(1)) as read:
                group = read.fetch_next()
                bool_values = np.from_dlpack(group.dlpack(0)).copy()
                stage.release_group(group)
            # [/snippet:doc-read-usd-bool]

            # [snippet:doc-write-usd-bool]
            stage.write_attribute(
                query,
                attribute,
                ordinal=2,
                tensors=np.array([False], dtype=np.bool_),
                is_array=False,
            ).wait()
            stage.advance_write_floor(2, ovstage.Scope.ALL).wait()
            # [/snippet:doc-write-usd-bool]

            with stage.read_attributes(query, [attribute], ovstage.OrdinalRange.latest(2)) as read:
                group = read.fetch_next()
                updated = np.from_dlpack(group.dlpack(0)).copy()
                stage.release_group(group)
        paths.destroy_path_list(path_list)

    assert bool_values.shape == (1,)
    assert updated.tolist() == [False]


def test_extent_and_world_extent_are_readable(stage):
    """Local extent stays local; _worldExtent reflects the transform hierarchy."""
    ovstage.population.open_usd(stage, ALL_ATTRIBUTES_PATH, ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()

    with ovstage.PathDictionary(stage) as paths:
        path_list = paths.create_path_list_from_strings([EXTENT_LEAF])
        with stage.query_from_path_list(path_list) as query:
            local_attribute = paths.intern_token("extent")
            world_attribute = paths.intern_token("_worldExtent")

            # [snippet:doc-extent-world-extent]
            with stage.read_attributes(
                query, [local_attribute, world_attribute], ovstage.OrdinalRange.latest(1)
            ) as read:
                values = {}
                for group in read.groups():
                    values[group.attribute] = np.from_dlpack(group.dlpack(0)).copy()
                    stage.release_group(group)
            local_extent = values[local_attribute]
            world_extent = values[world_attribute]
            # [/snippet:doc-extent-world-extent]
        paths.destroy_path_list(path_list)

    expected_local = np.array([[-1, -2, -3, 1, 2, 3]], dtype=np.float64)
    expected_world = np.array([[8, 14, 18, 12, 26, 42]], dtype=np.float64)

    _assert_array_close("extent", local_extent, expected_local)
    _assert_array_close("_worldExtent", world_extent, expected_world)
