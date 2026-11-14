# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Compare Generic WPM recipes with independently authored usd-core equivalents."""

from pathlib import Path

import pytest
from conftest import _schema_plugin_dir
from pxr import Usd

# [snippet:doc-generic-wpm-imports-python]
from pxr import Sdf, UsdGeom, UsdRender
# [/snippet:doc-generic-wpm-imports-python]

DATA = Path(__file__).parent / "data"


def author_base(stage):
    # [snippet:doc-generic-wpm-base-python]
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(10)
    world = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(world)
    sensor = stage.DefinePrim("/World/Sensor", "OmniGeneralSensor")
    sensor.AddAppliedSchema("OmniSensorGenericWpmAPI")
    # Align the sensor's +X-forward basis with this Z-up world.
    sensor.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3, custom=False).Set((90, 0, -90))
    sensor.CreateAttribute(
        "xformOpOrder", Sdf.ValueTypeNames.TokenArray, custom=False, variability=Sdf.VariabilityUniform
    ).Set(["xformOp:rotateXYZ"])
    sensor.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set((10, 1))
    ns = "omni:sensor:GenericWpm:"
    sensor.CreateAttribute(ns + "maxBounces", Sdf.ValueTypeNames.UInt, custom=False).Set(1)
    sensor.CreateAttribute(ns + "maxHitDistanceM", Sdf.ValueTypeNames.Float, custom=False).Set(100)
    for name in ("activeTxPatternIndex", "activeRxPatternIndex", "activeMappingPageIndex"):
        sensor.CreateAttribute(ns + name, Sdf.ValueTypeNames.UInt, custom=False).Set(0)

    UsdGeom.Scope.Define(stage, "/Render")
    product = UsdRender.Product.Define(stage, "/Render/GenericWpm")
    product.CreateCameraRel().SetTargets(["/World/Sensor"])
    product.CreateOrderedVarsRel().SetTargets(["/Render/GenericWpm/Contributions"])
    output = UsdRender.Var.Define(stage, "/Render/GenericWpm/Contributions")
    output.CreateSourceNameAttr("Contributions")
    # Empty selects the default contribution channels.
    output.GetPrim().CreateAttribute("channels", Sdf.ValueTypeNames.TokenArray, custom=False).Set([])
    # [/snippet:doc-generic-wpm-base-python]


def author_depth(stage):
    # [snippet:doc-generic-wpm-depth-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    for role in ("tx", "rx"):
        sensor.CreateAttribute(ns + role + ":patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["grid"])
        grid = ns + "gridPatterns:" + role + ":"
        sensor.CreateAttribute(grid + "modes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["SPHERICAL"])
        sensor.CreateAttribute(grid + "numRows", Sdf.ValueTypeNames.UIntArray, custom=False).Set([3])
        sensor.CreateAttribute(grid + "numCols", Sdf.ValueTypeNames.UIntArray, custom=False).Set([5])
        sensor.CreateAttribute(grid + "startRowUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([-10])
        sensor.CreateAttribute(grid + "endRowUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([10])
        sensor.CreateAttribute(grid + "startColUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([-20])
        sensor.CreateAttribute(grid + "endColUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([20])
        sensor.CreateAttribute(grid + "layouts", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["rowMajor"])
        sensor.CreateAttribute(grid + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
        sensor.CreateAttribute(grid + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    sensor.CreateAttribute(ns + "ray:patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["free"])
    sensor.CreateAttribute(ns + "tx:rayPatternIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    sensor.CreateAttribute(ns + "tx:mappingModes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["1to1"])
    sensor.CreateAttribute(ns + "tx:mappingBloomFactors", Sdf.ValueTypeNames.UIntArray, custom=False).Set([])
    # One transmitter-relative +X ray follows each transmitter's orientation.
    ray = ns + "freePatterns:ray:"
    sensor.CreateAttribute(ray + "numElementsPerPattern", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1])
    sensor.CreateAttribute(ray + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
    sensor.CreateAttribute(ray + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    # [/snippet:doc-generic-wpm-depth-python]


def author_planar(stage):
    author_depth(stage)
    # [snippet:doc-generic-wpm-planar-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    for role in ("tx", "rx"):
        grid = "omni:sensor:GenericWpm:gridPatterns:" + role + ":"
        # Rows are Z positions and columns are Y positions, in meters.
        sensor.GetAttribute(grid + "modes").Set(["PLANAR"])
        sensor.GetAttribute(grid + "startRowUnits").Set([-1])
        sensor.GetAttribute(grid + "endRowUnits").Set([1])
        sensor.GetAttribute(grid + "startColUnits").Set([-2])
        sensor.GetAttribute(grid + "endColUnits").Set([2])
    # [/snippet:doc-generic-wpm-planar-python]


def author_cylindrical(stage):
    author_depth(stage)
    # [snippet:doc-generic-wpm-cylindrical-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    for role in ("tx", "rx"):
        grid = "omni:sensor:GenericWpm:gridPatterns:" + role + ":"
        # Rows span heights in meters; columns retain -20..20 degree azimuths.
        sensor.GetAttribute(grid + "modes").Set(["CYLINDRICAL"])
        sensor.GetAttribute(grid + "startRowUnits").Set([-1])
        sensor.GetAttribute(grid + "endRowUnits").Set([1])
    # [/snippet:doc-generic-wpm-cylindrical-python]


def author_lidar(stage):
    author_depth(stage)
    # [snippet:doc-generic-wpm-lidar-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    for role in ("tx", "rx"):
        grid = "omni:sensor:GenericWpm:gridPatterns:" + role + ":"
        # Full-circle azimuth excludes the duplicate +180-degree endpoint.
        sensor.GetAttribute(grid + "numRows").Set([4])
        sensor.GetAttribute(grid + "numCols").Set([16])
        sensor.GetAttribute(grid + "startColUnits").Set([-180])
        sensor.GetAttribute(grid + "endColUnits").Set([180])
        sensor.GetAttribute(grid + "layouts").Set(["columnMajor"])
    tx = "omni:sensor:GenericWpm:gridPatterns:tx:"
    sensor.CreateAttribute(tx + "startTimeOffsetsNs", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    sensor.CreateAttribute(tx + "endTimeOffsetsNs", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1000000])
    # [/snippet:doc-generic-wpm-lidar-python]


def author_gaussian(stage):
    author_depth(stage)
    # [snippet:doc-generic-wpm-gaussian-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    sensor.GetAttribute(ns + "ray:patternTypes").Set(["gaussian"])
    # Clear the inherited Free family when replacing its ray bundle.
    for name in ("numElementsPerPattern", "positions", "orientations"):
        sensor.GetAttribute(ns + "freePatterns:ray:" + name).Set([])
    ray = ns + "gaussianPatterns:ray:"
    sensor.CreateAttribute(ray + "numElements", Sdf.ValueTypeNames.UIntArray, custom=False).Set([9])
    sensor.CreateAttribute(ray + "seeds", Sdf.ValueTypeNames.UIntArray, custom=False).Set([7])
    sensor.CreateAttribute(ray + "stdDevsHorizontal", Sdf.ValueTypeNames.FloatArray, custom=False).Set([1])
    sensor.CreateAttribute(ray + "stdDevsVertical", Sdf.ValueTypeNames.FloatArray, custom=False).Set([0.5])
    sensor.CreateAttribute(ray + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
    sensor.CreateAttribute(ray + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    # Uniform firing offset from each transmitter, not propagation time.
    sensor.CreateAttribute(ray + "globalTimeOffsetsNs", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    # [/snippet:doc-generic-wpm-gaussian-python]


def author_gaussian_bloom(stage):
    author_gaussian(stage)
    # [snippet:doc-generic-wpm-gaussian-bloom-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    # Radius one allocates nine receiver slots per ray; edge slots can be invalid.
    sensor.GetAttribute("omni:sensor:GenericWpm:tx:mappingBloomFactors").Set([1])
    # [/snippet:doc-generic-wpm-gaussian-bloom-python]


def author_multistatic(stage):
    # [snippet:doc-generic-wpm-multistatic-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    # About 77 GHz in vacuum; material response depends on wavelength.
    sensor.CreateAttribute(ns + "wavelengthNm", Sdf.ValueTypeNames.Float, custom=False).Set(3900000)
    for role, positions in (("tx", [(0, -0.5, 0), (0, 0.5, 0)]), ("rx", [(0, -0.4, 0), (0, 0, 0), (0, 0.4, 0)])):
        sensor.CreateAttribute(ns + role + ":patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["free"])
        free = ns + "freePatterns:" + role + ":"
        sensor.CreateAttribute(free + "numElementsPerPattern", Sdf.ValueTypeNames.UIntArray, custom=False).Set(
            [len(positions)]
        )
        sensor.CreateAttribute(free + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set(positions)
        sensor.CreateAttribute(free + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set(
            [(0, 0, 0, 1)] * len(positions)
        )
    # Each transmitter emits the same nine transmitter-relative rays.
    sensor.CreateAttribute(ns + "ray:patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["grid"])
    ray = ns + "gridPatterns:ray:"
    sensor.CreateAttribute(ray + "modes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["SPHERICAL"])
    sensor.CreateAttribute(ray + "numRows", Sdf.ValueTypeNames.UIntArray, custom=False).Set([3])
    sensor.CreateAttribute(ray + "numCols", Sdf.ValueTypeNames.UIntArray, custom=False).Set([3])
    sensor.CreateAttribute(ray + "startRowUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([-5])
    sensor.CreateAttribute(ray + "endRowUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([5])
    sensor.CreateAttribute(ray + "startColUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([-5])
    sensor.CreateAttribute(ray + "endColUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([5])
    sensor.CreateAttribute(ray + "layouts", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["rowMajor"])
    sensor.CreateAttribute(ray + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
    sensor.CreateAttribute(ray + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    sensor.CreateAttribute(ns + "tx:rayPatternIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    sensor.CreateAttribute(ns + "tx:mappingModes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["nton"])
    # [/snippet:doc-generic-wpm-multistatic-python]


def author_multistatic_map(stage):
    author_multistatic(stage)
    # [snippet:doc-generic-wpm-multistatic-map-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    sensor.GetAttribute(ns + "tx:mappingModes").Set(["map"])
    sensor.CreateAttribute(ns + "tx:mappingTargetRxGroups", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    mapping = ns + "txRxMappings:"
    sensor.CreateAttribute(mapping + "numRxGroupsPerPages", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1])
    sensor.CreateAttribute(mapping + "numRxPerGroups", Sdf.ValueTypeNames.UIntArray, custom=False).Set([2])
    # Receiver-slot order is explicit and local to the selected Rx pattern.
    sensor.CreateAttribute(mapping + "rxIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set([2, 0])
    # [/snippet:doc-generic-wpm-multistatic-map-python]


def author_acoustic(stage):
    # [snippet:doc-generic-wpm-acoustic-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    sensor.CreateAttribute(ns + "waveType", Sdf.ValueTypeNames.Token, custom=False).Set("mechanical")
    # Operating wavelength: 6.7 mm.
    sensor.CreateAttribute(ns + "wavelengthNm", Sdf.ValueTypeNames.Float, custom=False).Set(6700000)
    for role in ("tx", "rx", "ray"):
        sensor.CreateAttribute(ns + role + ":patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["free"])
        free = ns + "freePatterns:" + role + ":"
        sensor.CreateAttribute(free + "numElementsPerPattern", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1])
        sensor.CreateAttribute(free + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
        sensor.CreateAttribute(free + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    sensor.CreateAttribute(ns + "tx:rayPatternIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    sensor.CreateAttribute(ns + "tx:mappingModes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["1to1"])
    # [/snippet:doc-generic-wpm-acoustic-python]


def author_mixed(stage):
    # [snippet:doc-generic-wpm-mixed-python]
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    # Role order consumes successive rows from each named family.
    sensor.CreateAttribute(ns + "tx:patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(
        ["free", "grid", "free"]
    )
    sensor.CreateAttribute(ns + "rx:patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["free", "grid"])
    sensor.CreateAttribute(ns + "ray:patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(
        ["free", "grid", "gaussian"]
    )
    for role, counts, positions in (
        ("tx", [1, 1], [(0, 0, 0), (0, 0.2, 0)]),
        ("rx", [3], [(0, -1, 0), (0, 0, 0), (0, 1, 0)]),
        ("ray", [1], [(0, 0, 0)]),
    ):
        free = ns + "freePatterns:" + role + ":"
        sensor.CreateAttribute(free + "numElementsPerPattern", Sdf.ValueTypeNames.UIntArray, custom=False).Set(counts)
        sensor.CreateAttribute(free + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set(positions)
        sensor.CreateAttribute(free + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set(
            [(0, 0, 0, 1)] * len(positions)
        )
    for role, mode, columns, first, last in (
        ("tx", "PLANAR", 2, -0.5, 0.5),
        ("rx", "PLANAR", 2, -0.5, 0.5),
        ("ray", "SPHERICAL", 3, -5, 5),
    ):
        grid = ns + "gridPatterns:" + role + ":"
        sensor.CreateAttribute(grid + "modes", Sdf.ValueTypeNames.TokenArray, custom=False).Set([mode])
        sensor.CreateAttribute(grid + "numRows", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1])
        sensor.CreateAttribute(grid + "numCols", Sdf.ValueTypeNames.UIntArray, custom=False).Set([columns])
        sensor.CreateAttribute(grid + "startRowUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([0])
        sensor.CreateAttribute(grid + "endRowUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([0])
        sensor.CreateAttribute(grid + "startColUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([first])
        sensor.CreateAttribute(grid + "endColUnits", Sdf.ValueTypeNames.FloatArray, custom=False).Set([last])
        sensor.CreateAttribute(grid + "layouts", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["rowMajor"])
        sensor.CreateAttribute(grid + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
        sensor.CreateAttribute(grid + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    ray = ns + "gaussianPatterns:ray:"
    sensor.CreateAttribute(ray + "numElements", Sdf.ValueTypeNames.UIntArray, custom=False).Set([9])
    sensor.CreateAttribute(ray + "seeds", Sdf.ValueTypeNames.UIntArray, custom=False).Set([7])
    sensor.CreateAttribute(ray + "stdDevsHorizontal", Sdf.ValueTypeNames.FloatArray, custom=False).Set([1])
    sensor.CreateAttribute(ray + "stdDevsVertical", Sdf.ValueTypeNames.FloatArray, custom=False).Set([0.5])
    sensor.CreateAttribute(ray + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
    sensor.CreateAttribute(ray + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    # Tx role patterns 0, 1, 2 select Free, Grid, Gaussian ray bundles.
    sensor.CreateAttribute(ns + "tx:rayPatternIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0, 1, 2])
    sensor.CreateAttribute(ns + "tx:mappingModes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(
        ["map", "map", "map"]
    )
    sensor.CreateAttribute(ns + "tx:mappingTargetRxGroups", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1, 0, 1])
    mapping = ns + "txRxMappings:"
    sensor.CreateAttribute(mapping + "numRxGroupsPerPages", Sdf.ValueTypeNames.UIntArray, custom=False).Set([2, 2])
    sensor.CreateAttribute(mapping + "numRxPerGroups", Sdf.ValueTypeNames.UIntArray, custom=False).Set([3, 2, 1, 2])
    # Page 0: [0,1,2], [2,0]. Page 1: [1], [0,1].
    sensor.CreateAttribute(mapping + "rxIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set(
        [0, 1, 2, 2, 0, 1, 0, 1]
    )
    # [/snippet:doc-generic-wpm-mixed-python]


RECIPES = [
    ("depth", author_depth, [15], [15], [1]),
    ("planar", author_planar, [15], [15], [1]),
    ("cylindrical", author_cylindrical, [15], [15], [1]),
    ("lidar", author_lidar, [64], [64], [1]),
    ("gaussian", author_gaussian, [15], [15], [9]),
    ("gaussian_bloom", author_gaussian_bloom, [15], [15], [9]),
    ("multistatic", author_multistatic, [2], [3], [9]),
    ("multistatic_map", author_multistatic_map, [2], [3], [9]),
    ("acoustic", author_acoustic, [1], [1], [1]),
    ("mixed", author_mixed, [1, 2, 1], [3, 2], [1, 3, 9]),
]


def _assert_same_authored_stage(actual, expected):
    assert not expected.GetCompositionErrors()
    assert {p.GetPath() for p in actual.Traverse()} == {p.GetPath() for p in expected.Traverse()}
    for name in ("defaultPrim", "metersPerUnit", "upAxis", "timeCodesPerSecond"):
        assert actual.GetMetadata(name) == expected.GetMetadata(name), name
    for reference in expected.Traverse():
        prim = actual.GetPrimAtPath(reference.GetPath())
        assert prim.GetTypeName() == reference.GetTypeName()
        assert prim.GetMetadata("apiSchemas") == reference.GetMetadata("apiSchemas")
        assert {a.GetName() for a in prim.GetAuthoredAttributes()} == {
            a.GetName() for a in reference.GetAuthoredAttributes()
        }
        for attr in reference.GetAuthoredAttributes():
            equivalent = prim.GetAttribute(attr.GetName())
            assert equivalent.GetTypeName() == attr.GetTypeName(), attr.GetPath()
            assert equivalent.GetVariability() == attr.GetVariability(), attr.GetPath()
            assert equivalent.IsCustom() == attr.IsCustom(), attr.GetPath()
            assert equivalent.Get() == attr.Get(), attr.GetPath()
        assert {r.GetName() for r in prim.GetAuthoredRelationships()} == {
            r.GetName() for r in reference.GetAuthoredRelationships()
        }
        for rel in reference.GetAuthoredRelationships():
            assert prim.GetRelationship(rel.GetName()).GetTargets() == rel.GetTargets()


def _role_counts(sensor, role):
    ns = "omni:sensor:GenericWpm:"
    counts = []
    rows = {"free": 0, "grid": 0, "gaussian": 0}
    for family in sensor.GetAttribute(ns + role + ":patternTypes").Get():
        prefix = ns + family + "Patterns:" + role + ":"
        row = rows[family]
        if family == "free":
            counts.append(sensor.GetAttribute(prefix + "numElementsPerPattern").Get()[row])
        elif family == "grid":
            counts.append(
                sensor.GetAttribute(prefix + "numRows").Get()[row] * sensor.GetAttribute(prefix + "numCols").Get()[row]
            )
        else:
            counts.append(sensor.GetAttribute(prefix + "numElements").Get()[row])
        rows[family] += 1
    return counts


def test_generic_wpm_base_python_matches_usda():
    stage = Usd.Stage.CreateInMemory()
    author_base(stage)
    _assert_same_authored_stage(stage, Usd.Stage.Open(str(DATA / "generic_wpm_base.usda")))


@pytest.mark.parametrize("name,author,tx,rx,ray", RECIPES, ids=[r[0] for r in RECIPES])
def test_generic_wpm_python_matches_composed_usda(name, author, tx, rx, ray):
    stage = Usd.Stage.CreateInMemory()
    author_base(stage)
    author(stage)
    _assert_same_authored_stage(stage, Usd.Stage.Open(str(DATA / f"generic_wpm_{name}.usda")))
    sensor = stage.GetPrimAtPath("/World/Sensor")
    assert _role_counts(sensor, "tx") == tx
    assert _role_counts(sensor, "rx") == rx
    assert _role_counts(sensor, "ray") == ray
    assert [str(p.GetPath()) for p in stage.Traverse() if p.IsA(UsdRender.Var)] == ["/Render/GenericWpm/Contributions"]


def test_generic_wpm_recipe_attributes_match_schema_declarations():
    schema = Sdf.Layer.FindOrOpen(str(_schema_plugin_dir("omni_sensors") / "generatedSchema.usda"))
    assert schema, "The tested SDK must include the Generic WPM schemas"
    declared_types = {}
    for prim in schema.rootPrims:
        if prim.name.startswith("OmniSensorGenericWpm"):
            for attr in prim.attributes:
                for role in ("tx", "rx", "ray"):
                    declared_types[attr.name.replace("__INSTANCE_NAME__", role)] = attr.typeName
    for name, *_ in RECIPES:
        stage = Usd.Stage.Open(str(DATA / f"generic_wpm_{name}.usda"))
        for attr in stage.GetPrimAtPath("/World/Sensor").GetAuthoredAttributes():
            if attr.GetName().startswith("omni:sensor:GenericWpm:"):
                assert declared_types.get(attr.GetName()) == attr.GetTypeName(), (name, attr.GetName())


def test_generic_wpm_mixed_mapping_pages_and_role_order():
    stage = Usd.Stage.Open(str(DATA / "generic_wpm_mixed.usda"))
    sensor = stage.GetPrimAtPath("/World/Sensor")
    ns = "omni:sensor:GenericWpm:"
    assert list(sensor.GetAttribute(ns + "tx:rayPatternIndices").Get()) == [0, 1, 2]
    assert list(sensor.GetAttribute(ns + "tx:mappingTargetRxGroups").Get()) == [1, 0, 1]
    mapping = ns + "txRxMappings:"
    assert list(sensor.GetAttribute(mapping + "numRxGroupsPerPages").Get()) == [2, 2]
    assert list(sensor.GetAttribute(mapping + "numRxPerGroups").Get()) == [3, 2, 1, 2]
    assert list(sensor.GetAttribute(mapping + "rxIndices").Get()) == [0, 1, 2, 2, 0, 1, 0, 1]
    # Each selected group is addressed within its page, not the packed group array.
    pages = [[[0, 1, 2], [2, 0]], [[1], [0, 1]]]
    for tx, rx, page in ((0, 0, 0), (1, 1, 1), (2, 1, 1)):
        group = [1, 0, 1][tx]
        assert all(index < [3, 2][rx] for index in pages[page][group])
    assert max(pages[0][1]) >= 2  # (Tx=0, Rx=1, page=0) is the rejected-edit example.


def author_minimal(stage):
    # [snippet:doc-generic-wpm-minimal-python]
    sensor = stage.DefinePrim("/Sensor", "OmniGeneralSensor")
    sensor.AddAppliedSchema("OmniSensorGenericWpmAPI")
    ns = "omni:sensor:GenericWpm:"
    for role in ("tx", "rx", "ray"):
        sensor.CreateAttribute(ns + role + ":patternTypes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["free"])
        free = ns + "freePatterns:" + role + ":"
        sensor.CreateAttribute(free + "numElementsPerPattern", Sdf.ValueTypeNames.UIntArray, custom=False).Set([1])
        sensor.CreateAttribute(free + "positions", Sdf.ValueTypeNames.Float3Array, custom=False).Set([(0, 0, 0)])
        sensor.CreateAttribute(free + "orientations", Sdf.ValueTypeNames.Float4Array, custom=False).Set([(0, 0, 0, 1)])
    sensor.CreateAttribute(ns + "tx:rayPatternIndices", Sdf.ValueTypeNames.UIntArray, custom=False).Set([0])
    sensor.CreateAttribute(ns + "tx:mappingModes", Sdf.ValueTypeNames.TokenArray, custom=False).Set(["1to1"])
    # [/snippet:doc-generic-wpm-minimal-python]


def test_generic_wpm_minimal_python_matches_usda():
    stage = Usd.Stage.CreateInMemory()
    author_minimal(stage)
    _assert_same_authored_stage(stage, Usd.Stage.Open(str(DATA / "generic_wpm_minimal.usda")))
    sensor = stage.GetPrimAtPath("/Sensor")
    for role in ("tx", "rx", "ray"):
        assert _role_counts(sensor, role) == [1]
