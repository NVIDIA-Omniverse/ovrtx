# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
"""Check that the two authoring tabs produce equivalent USD opinions.

These are authoring/composition checks, not sensor-runtime validation.
"""

from pathlib import Path
import shutil
import textwrap
from pxr import Sdf, Usd

DATA = Path(__file__).parent / "data/nonvisual"
PROFILES = Path(__file__).parents[3] / "docs/sensors/nonvisual/lidar_core/tutorials/assets"


def _stage_with_profiles(tmp_path):
    for name in (
        "Blickfeld_Cube1_Analytic.usda",
        "SICK_TiM781.usda",
        "Velodyne_Alpha_Prime_Rev4.usda",
    ):
        shutil.copyfile(PROFILES / name, tmp_path / name)
    return Usd.Stage.CreateNew(str(tmp_path / "authored.usda"))


def _assert_authored_layer(actual, expected_path):
    expected = (
        expected_path
        if isinstance(expected_path, Sdf.Layer)
        else Sdf.Layer.FindOrOpen(str(expected_path))
    )
    paths = []
    expected.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    actual_paths = []
    actual.Traverse(Sdf.Path.absoluteRootPath, actual_paths.append)
    assert set(actual_paths) == set(paths)
    for path in paths:
        a, b = actual.GetObjectAtPath(path), expected.GetObjectAtPath(path)
        if a is None or b is None:
            assert a is None and b is None, path
            continue  # Relationship target paths are compared on their owning spec.
        assert set(a.ListInfoKeys()) == set(b.ListInfoKeys()), path
        for key in b.ListInfoKeys():
            assert a.GetInfo(key) == b.GetInfo(key), (path, key)


def test_acoustic_wpm_howto_array_topology_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-acoustic-wpm-howto-array-topology-1-python]
    from pxr import Gf, Sdf

    acoustic_array = stage.DefinePrim("/acoustic_array", "OmniAcoustic")
    acoustic_array.AddAppliedSchema("OmniSensorGenericAcousticWpmAPI")
    acoustic_array.AddAppliedSchema("OmniSensorWpmAcousticSensorMountAPI:m002")
    acoustic_array.AddAppliedSchema("OmniSensorWpmAcousticRxGroupAPI:g002")
    # The main schema supplies m001; override its position and rotation.
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:sensorMount:m001:position", Sdf.ValueTypeNames.Float3, custom=False
    ).Set(Gf.Vec3f(4.0, 0.5, 0.5))
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:sensorMount:m001:rotation", Sdf.ValueTypeNames.Float3, custom=False
    ).Set(Gf.Vec3f(0.0, -1.0, 0.0))
    # m002 is the second mount, applied above.
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:sensorMount:m002:position", Sdf.ValueTypeNames.Float3, custom=False
    ).Set(Gf.Vec3f(4.0, -0.5, 0.5))
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:sensorMount:m002:rotation", Sdf.ValueTypeNames.Float3, custom=False
    ).Set(Gf.Vec3f(0.0, -1.0, 0.0))
    # Both groups listen with both mounts, in sorted mount order.
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:rxGroup:g001:receiverIndices",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([0, 1])
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:rxGroup:g002:receiverIndices",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([0, 1])
    # Two events: mount 0 fires on channel 0; mount 1 follows 5 microseconds later on channel 1.
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:firingSeq:seq001:eventTimeNs",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([0.0, 5000.0])
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:firingSeq:seq001:txSensorId",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([0, 1])
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:firingSeq:seq001:rxGroupId",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([0, 1])
    acoustic_array.CreateAttribute(
        "omni:sensor:WpmAcoustic:firingSeq:seq001:channel",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([0, 1])
    # [/snippet:doc-nonvisual-acoustic-wpm-howto-array-topology-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "acoustic_wpm_howto_array_topology_1.usda")


def test_lidar_core_howto_field_of_view_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-howto-field-of-view-1-python]
    from pxr import Gf, Sdf

    generic_lidar = stage.DefinePrim("/generic_lidar", "OmniLidar")
    generic_lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:nearRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.3)
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:farRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(200.0)
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:validStartAzimuthDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:validEndAzimuthDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(360.0)
    # [/snippet:doc-nonvisual-lidar-core-howto-field-of-view-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_howto_field_of_view_1.usda")


def test_lidar_core_howto_firing_pattern_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-howto-firing-pattern-1-python]
    from pxr import Gf, Sdf

    generic_lidar = stage.DefinePrim("/generic_lidar", "OmniLidar")
    generic_lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    generic_lidar.CreateAttribute(
        "omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False
    ).Set(Gf.Vec2d(10.0, 1.0))
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:rotPatternFiringResDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.1)
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:numberOfEmitters", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:numberOfChannels", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:azimuthDeg", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([0.0, 0.0])
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:elevationDeg",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([-1.0, 1.0])
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:fireTimeNs", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([0, 1000])
    generic_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:channelId", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([1, 2])
    # [/snippet:doc-nonvisual-lidar-core-howto-firing-pattern-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_howto_firing_pattern_1.usda")


def test_lidar_core_howto_firing_pattern_2(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-howto-firing-pattern-2-python]
    from pxr import Gf, Sdf

    two_state_lidar = stage.DefinePrim("/two_state_lidar", "OmniLidar")
    two_state_lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    two_state_lidar.AddAppliedSchema("OmniSensorGenericLidarCoreEmitterStateAPI:s002")
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:numberOfEmitters", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:numberOfChannels", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:stateResolutionStep", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:azimuthDeg", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([0.0, 0.0])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:elevationDeg",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([-1.0, 1.0])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:fireTimeNs", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([0, 1000])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:channelId", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([1, 2])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s002:azimuthDeg", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([0.0, 0.0])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s002:elevationDeg",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([-2.0, 2.0])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s002:fireTimeNs", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([0, 1000])
    two_state_lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s002:channelId", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([1, 2])
    # [/snippet:doc-nonvisual-lidar-core-howto-firing-pattern-2-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_howto_firing_pattern_2.usda")


def test_lidar_core_howto_intensity_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-howto-intensity-1-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/lidar", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityProcessing", Sdf.ValueTypeNames.Token, custom=False
    ).Set("NORMALIZATION")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityScalePercent", Sdf.ValueTypeNames.Float, custom=False
    ).Set(255.0)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectance", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.1)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectionRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(200.0)
    # [/snippet:doc-nonvisual-lidar-core-howto-intensity-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_howto_intensity_1.usda")


def test_lidar_core_howto_motion_artifacts_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-howto-motion-artifacts-1-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Lidar", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    lidar.CreateAttribute(
        "omni:sensor:Core:outputMotionCompensationState", Sdf.ValueTypeNames.Token, custom=False
    ).Set("NONCOMPENSATED")
    # [/snippet:doc-nonvisual-lidar-core-howto-motion-artifacts-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_howto_motion_artifacts_1.usda")


def test_lidar_core_tutorials_blickfeld_cube1_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-1-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Blickfeld_Cube1_Analytic", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    lidar.CreateAttribute("omni:sensor:modelName", Sdf.ValueTypeNames.String, custom=False).Set(
        "LidarCore"
    )
    lidar.CreateAttribute("omni:sensor:modelVersion", Sdf.ValueTypeNames.String, custom=False).Set(
        "0"
    )
    lidar.CreateAttribute("omni:sensor:modelVendor", Sdf.ValueTypeNames.String, custom=False).Set(
        "NVIDIA"
    )
    lidar.CreateAttribute("omni:sensor:marketName", Sdf.ValueTypeNames.String, custom=False).Set(
        "Blickfeld Cube 1"
    )
    lidar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    lidar.CreateAttribute("omni:sensor:Core:scanType", Sdf.ValueTypeNames.Token, custom=False).Set(
        "SOLID_STATE"
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:partialOutputs", Sdf.ValueTypeNames.Bool, custom=False
    ).Set(False)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-1-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_blickfeld_cube1_1.usda"
    )


def test_lidar_core_tutorials_blickfeld_cube1_2(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-2-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Blickfeld_Cube1_Analytic", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:numberOfEmitters", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(5850)
    lidar.CreateAttribute(
        "omni:sensor:Core:numberOfChannels", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(5850)
    lidar.CreateAttribute("omni:sensor:Core:numLines", Sdf.ValueTypeNames.UInt, custom=False).Set(
        50
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:numRaysPerLine", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set(
        [
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
            117,
        ]
    )
    # [/snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-2-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_blickfeld_cube1_2.usda"
    )


def test_lidar_core_tutorials_blickfeld_cube1_3(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-3-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Blickfeld_Cube1_Analytic", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:nearRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(1.5)
    lidar.CreateAttribute("omni:sensor:Core:farRangeM", Sdf.ValueTypeNames.Float, custom=False).Set(
        250.0
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rangeResolutionM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.01)
    lidar.CreateAttribute(
        "omni:sensor:Core:rangeAccuracyM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.02)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectance", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.1)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectionRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(30.0)
    lidar.CreateAttribute("omni:sensor:Core:rangeCount", Sdf.ValueTypeNames.UInt, custom=False).Set(
        1
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rangesMinM", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([1.5])
    lidar.CreateAttribute(
        "omni:sensor:Core:rangesMaxM", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([250.0])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-3-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_blickfeld_cube1_3.usda"
    )


def test_lidar_core_tutorials_blickfeld_cube1_4(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-4-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Blickfeld_Cube1_Analytic", "OmniLidar")
    lidar.CreateAttribute("omni:sensor:Core:rayType", Sdf.ValueTypeNames.Token, custom=False).Set(
        "IDEALIZED"
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:waveLengthNm", Sdf.ValueTypeNames.Float, custom=False
    ).Set(905.0)
    lidar.CreateAttribute(
        "omni:sensor:Core:divergenceHorDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.4)
    lidar.CreateAttribute(
        "omni:sensor:Core:divergenceVerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.4)
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityProcessing", Sdf.ValueTypeNames.Token, custom=False
    ).Set("NORMALIZATION")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityMappingType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("LINEAR")
    lidar.CreateAttribute("omni:sensor:Core:maxReturns", Sdf.ValueTypeNames.UInt, custom=False).Set(
        3
    )
    # [/snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-4-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_blickfeld_cube1_4.usda"
    )


def test_lidar_core_tutorials_blickfeld_cube1_5(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-5-python]
    from pxr import Gf, Sdf

    stage.SetMetadata("upAxis", "Z")
    stage.SetMetadata("defaultPrim", "World")
    stage.SetMetadata("metersPerUnit", 1.0)
    world = stage.DefinePrim("/World", "Xform")

    cube1 = stage.OverridePrim("/World/Cube1")
    # Reference the profile default prim; keep the profile beside this layer.
    cube1.GetReferences().AddReference("./Blickfeld_Cube1_Analytic.usda")
    cube1.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 0.0, 0.5)
    )
    cube1.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate"])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-blickfeld-cube1-5-python]
    sensor = stage.GetPrimAtPath("/World/Cube1")
    assert sensor.GetTypeName() == "OmniLidar"
    assert (
        "OmniSensorGenericLidarCoreAPI"
        in sensor.GetMetadata("apiSchemas").GetAddedOrExplicitItems()
    )
    assert sensor.GetAttribute("omni:sensor:Core:emitterState:s001:azimuthDeg").Get()
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_blickfeld_cube1_5.usda"
    )


def test_lidar_core_tutorials_sick_tim781_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-1-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    lidar.CreateAttribute("omni:sensor:modelName", Sdf.ValueTypeNames.String, custom=False).Set(
        "LidarCore"
    )
    lidar.CreateAttribute("omni:sensor:modelVersion", Sdf.ValueTypeNames.String, custom=False).Set(
        "0"
    )
    lidar.CreateAttribute("omni:sensor:modelVendor", Sdf.ValueTypeNames.String, custom=False).Set(
        "NVIDIA"
    )
    lidar.CreateAttribute("omni:sensor:marketName", Sdf.ValueTypeNames.String, custom=False).Set(
        "SICK TiM781-2174101"
    )
    lidar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(15.0, 1.0)
    )
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_1.usda")


def test_lidar_core_tutorials_sick_tim781_2(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-2-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781", "OmniLidar")
    lidar.CreateAttribute("omni:sensor:Core:scanType", Sdf.ValueTypeNames.Token, custom=False).Set(
        "ROTARY"
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rotationDirection", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CCW")
    lidar.CreateAttribute(
        "omni:sensor:Core:rotPatternFiringResDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.3333333)
    lidar.CreateAttribute(
        "omni:sensor:Core:numberOfEmitters", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    lidar.CreateAttribute(
        "omni:sensor:Core:numberOfChannels", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-2-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_2.usda")


def test_lidar_core_tutorials_sick_tim781_3(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-3-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781_SolidState", "OmniLidar")
    lidar.CreateAttribute("omni:sensor:Core:scanType", Sdf.ValueTypeNames.Token, custom=False).Set(
        "SOLID_STATE"
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:numberOfEmitters", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(811)
    lidar.CreateAttribute(
        "omni:sensor:Core:numberOfChannels", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(811)
    lidar.CreateAttribute("omni:sensor:Core:numLines", Sdf.ValueTypeNames.UInt, custom=False).Set(1)
    lidar.CreateAttribute(
        "omni:sensor:Core:numRaysPerLine", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([811])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-3-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_3.usda")


def test_lidar_core_tutorials_sick_tim781_4(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-4-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:rotationDirection", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CCW")
    lidar.CreateAttribute(
        "omni:sensor:Core:startAzimuthOffsetDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(90.0)
    lidar.CreateAttribute(
        "omni:sensor:Core:validStartAzimuthDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(44.9999)
    lidar.CreateAttribute(
        "omni:sensor:Core:validEndAzimuthDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(315.0001)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-4-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_4.usda")


def test_lidar_core_tutorials_sick_tim781_5(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-5-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:azimuthDeg", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([0.0])
    lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:elevationDeg",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([0.0])
    lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:vertOffsetM",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([0.06246])
    lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:fireTimeNs", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([0])
    lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:channelId", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([1])
    lidar.CreateAttribute(
        "omni:sensor:Core:emitterState:s001:rangeId", Sdf.ValueTypeNames.UIntArray, custom=False
    ).Set([0])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-5-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_5.usda")


def test_lidar_core_tutorials_sick_tim781_6(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-6-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:nearRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.05)
    lidar.CreateAttribute("omni:sensor:Core:farRangeM", Sdf.ValueTypeNames.Float, custom=False).Set(
        25.0
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rangeResolutionM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.001)
    lidar.CreateAttribute(
        "omni:sensor:Core:rangeAccuracyM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.02)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectance", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.1)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectionRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(8.0)
    lidar.CreateAttribute("omni:sensor:Core:maxReturns", Sdf.ValueTypeNames.UInt, custom=False).Set(
        1
    )
    lidar.CreateAttribute("omni:sensor:Core:rangeCount", Sdf.ValueTypeNames.UInt, custom=False).Set(
        1
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rangesMinM", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([0.05])
    lidar.CreateAttribute(
        "omni:sensor:Core:rangesMaxM", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([25.0])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-6-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_6.usda")


def test_lidar_core_tutorials_sick_tim781_7(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-7-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/SICK_TiM781", "OmniLidar")
    lidar.CreateAttribute("omni:sensor:Core:rayType", Sdf.ValueTypeNames.Token, custom=False).Set(
        "IDEALIZED"
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:waveLengthNm", Sdf.ValueTypeNames.Float, custom=False
    ).Set(850.0)
    lidar.CreateAttribute(
        "omni:sensor:Core:divergenceHorDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.8251)
    lidar.CreateAttribute(
        "omni:sensor:Core:divergenceVerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.4927)
    lidar.CreateAttribute(
        "omni:sensor:Core:peakPowerW", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.88)
    lidar.CreateAttribute(
        "omni:sensor:Core:pulseTimeNs", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(5)
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityProcessing", Sdf.ValueTypeNames.Token, custom=False
    ).Set("NORMALIZATION")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityMappingType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("LINEAR")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityScalePercent", Sdf.ValueTypeNames.Float, custom=False
    ).Set(254.0)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-7-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_7.usda")


def test_lidar_core_tutorials_sick_tim781_8(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-8-python]
    from pxr import Gf, Sdf

    stage.SetMetadata("upAxis", "Z")
    stage.SetMetadata("defaultPrim", "World")
    stage.SetMetadata("metersPerUnit", 1.0)
    world = stage.DefinePrim("/World", "Xform")

    ti_m781 = stage.OverridePrim("/World/TiM781")
    # Reference the profile default prim; keep the profile beside this layer.
    ti_m781.GetReferences().AddReference("./SICK_TiM781.usda")
    ti_m781.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 0.0, 0.5)
    )
    ti_m781.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate"])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-sick-tim781-8-python]
    sensor = stage.GetPrimAtPath("/World/TiM781")
    assert sensor.GetTypeName() == "OmniLidar"
    assert (
        "OmniSensorGenericLidarCoreAPI"
        in sensor.GetMetadata("apiSchemas").GetAddedOrExplicitItems()
    )
    assert sensor.GetAttribute("omni:sensor:Core:emitterState:s001:azimuthDeg").Get()
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_core_tutorials_sick_tim781_8.usda")


def test_lidar_core_tutorials_velodyne_alpha_prime_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Velodyne_Alpha_Prime_Rev4", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    lidar.CreateAttribute("omni:sensor:modelName", Sdf.ValueTypeNames.String, custom=False).Set(
        "LidarCore"
    )
    lidar.CreateAttribute("omni:sensor:modelVersion", Sdf.ValueTypeNames.String, custom=False).Set(
        "0"
    )
    lidar.CreateAttribute("omni:sensor:modelVendor", Sdf.ValueTypeNames.String, custom=False).Set(
        "NVIDIA"
    )
    lidar.CreateAttribute("omni:sensor:marketName", Sdf.ValueTypeNames.String, custom=False).Set(
        "Velodyne Alpha Prime Rev 4 (VLS-128)"
    )
    lidar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-1-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_velodyne_alpha_prime_1.usda"
    )


def test_lidar_core_tutorials_velodyne_alpha_prime_2(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Velodyne_Alpha_Prime_Rev4", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:rotationDirection", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CW")
    lidar.CreateAttribute(
        "omni:sensor:Core:startAzimuthOffsetDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(270.0)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-2-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_velodyne_alpha_prime_2.usda"
    )


def test_lidar_core_tutorials_velodyne_alpha_prime_3(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Velodyne_Alpha_Prime_Rev4", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:nearRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.3)
    lidar.CreateAttribute("omni:sensor:Core:farRangeM", Sdf.ValueTypeNames.Float, custom=False).Set(
        300.0
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rangeResolutionM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.004)
    lidar.CreateAttribute(
        "omni:sensor:Core:rangeAccuracyM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.03)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectance", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.1)
    lidar.CreateAttribute(
        "omni:sensor:Core:minReflectionRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(300.0)
    lidar.CreateAttribute("omni:sensor:Core:maxReturns", Sdf.ValueTypeNames.UInt, custom=False).Set(
        2
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:minDistBetweenEchosM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(1.0)
    lidar.CreateAttribute("omni:sensor:Core:rangeCount", Sdf.ValueTypeNames.UInt, custom=False).Set(
        1
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:rangesMinM", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([0.3])
    lidar.CreateAttribute(
        "omni:sensor:Core:rangesMaxM", Sdf.ValueTypeNames.FloatArray, custom=False
    ).Set([300.0])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-3-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_velodyne_alpha_prime_3.usda"
    )


def test_lidar_core_tutorials_velodyne_alpha_prime_4(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Velodyne_Alpha_Prime_Rev4", "OmniLidar")
    lidar.CreateAttribute("omni:sensor:Core:rayType", Sdf.ValueTypeNames.Token, custom=False).Set(
        "IDEALIZED"
    )
    lidar.CreateAttribute(
        "omni:sensor:Core:divergenceHorDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.1197482)
    lidar.CreateAttribute(
        "omni:sensor:Core:divergenceVerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.06016057)
    lidar.CreateAttribute(
        "omni:sensor:Core:waveLengthNm", Sdf.ValueTypeNames.Float, custom=False
    ).Set(905.0)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-4-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_velodyne_alpha_prime_4.usda"
    )


def test_lidar_core_tutorials_velodyne_alpha_prime_5(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5-python]
    from pxr import Gf, Sdf

    lidar = stage.DefinePrim("/Velodyne_Alpha_Prime_Rev4", "OmniLidar")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityProcessing", Sdf.ValueTypeNames.Token, custom=False
    ).Set("NORMALIZATION")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityMappingType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("LINEAR")
    lidar.CreateAttribute(
        "omni:sensor:Core:intensityScalePercent", Sdf.ValueTypeNames.Float, custom=False
    ).Set(255.0)
    # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-5-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_velodyne_alpha_prime_5.usda"
    )


def test_lidar_core_tutorials_velodyne_alpha_prime_6(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6-python]
    from pxr import Gf, Sdf

    stage.SetMetadata("upAxis", "Z")
    stage.SetMetadata("defaultPrim", "World")
    stage.SetMetadata("metersPerUnit", 1.0)
    world = stage.DefinePrim("/World", "Xform")

    sensors = stage.DefinePrim("/World/Sensors", "Xform")

    alpha_prime = stage.OverridePrim("/World/Sensors/AlphaPrime")
    # Reference the profile default prim; keep the profile beside this layer.
    alpha_prime.GetReferences().AddReference("./Velodyne_Alpha_Prime_Rev4.usda")
    alpha_prime.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 0.0, 2.0)
    )
    alpha_prime.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate"])
    # [/snippet:doc-nonvisual-lidar-core-tutorials-velodyne-alpha-prime-6-python]
    sensor = stage.GetPrimAtPath("/World/Sensors/AlphaPrime")
    assert sensor.GetTypeName() == "OmniLidar"
    assert (
        "OmniSensorGenericLidarCoreAPI"
        in sensor.GetMetadata("apiSchemas").GetAddedOrExplicitItems()
    )
    assert sensor.GetAttribute("omni:sensor:Core:emitterState:s001:azimuthDeg").Get()
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "lidar_core_tutorials_velodyne_alpha_prime_6.usda"
    )


def test_lidar_wpm_howto_tile_lidars_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-lidar-wpm-howto-tile-lidars-1-python]
    from pxr import Gf, Sdf

    # This scene uses meters and a Z-up world.
    stage.SetMetadata("metersPerUnit", 1.0)
    stage.SetMetadata("upAxis", "Z")

    sensor = stage.DefinePrim("/Sensor", "Xform")

    lidar = stage.DefinePrim("/Sensor/Lidar", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarWpmAPI")
    lidar.CreateAttribute("visibility", Sdf.ValueTypeNames.Token, custom=False).Set("invisible")
    lidar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:scanType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("solidState")
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:maxReturns", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    # Tile zero supplies the shared profile; keep every second firing row.
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:tiledSubSampling", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:firingPattern:p001:azimuthDeg",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([0.0, 0.0])
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:firingPattern:p001:elevationDeg",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([0.0, 0.0])
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:firingPattern:p001:fireTimeNs",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([0, 1000])
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:firingPattern:p001:channelId",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([1, 4])
    lidar.CreateAttribute(
        "omni:sensor:LidarWpm:firingPattern:p001:rangeId",
        Sdf.ValueTypeNames.UIntArray,
        custom=False,
    ).Set([])
    lidar.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, -4.0, 1.0)
    )
    lidar.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3, custom=False).Set(
        Gf.Vec3f(90.0, 0.0, -90.0)
    )
    lidar.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate", "xformOp:rotateXYZ"])

    # The other tile contributes only its placement and motion.
    lidar_tile1 = stage.DefinePrim("/Sensor/LidarTile1", "OmniLidar")
    lidar_tile1.AddAppliedSchema("OmniSensorGenericLidarWpmAPI")
    lidar_tile1.CreateAttribute("visibility", Sdf.ValueTypeNames.Token, custom=False).Set(
        "invisible"
    )
    lidar_tile1.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 4.0, 2.0)
    )
    lidar_tile1.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3, custom=False).Set(
        Gf.Vec3f(90.0, 0.0, -90.0)
    )
    lidar_tile1.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate", "xformOp:rotateXYZ"])

    outputs = stage.DefinePrim("/Sensor/Outputs", "Scope")

    product = stage.DefinePrim("/Sensor/Outputs/Product", "RenderProduct")
    product.CreateRelationship("camera", custom=False).SetTargets(
        ["/Sensor/Lidar", "/Sensor/LidarTile1"]
    )
    product.CreateRelationship("orderedVars", custom=False).SetTargets(
        ["/Sensor/Outputs/PointCloud"]
    )

    point_cloud = stage.DefinePrim("/Sensor/Outputs/PointCloud", "RenderVar")
    point_cloud.CreateAttribute(
        "sourceName", Sdf.ValueTypeNames.String, custom=False, variability=Sdf.VariabilityUniform
    ).Set("PointCloud")
    point_cloud.CreateAttribute("channels", Sdf.ValueTypeNames.TokenArray, custom=False).Set([])
    # [/snippet:doc-nonvisual-lidar-wpm-howto-tile-lidars-1-python]
    _assert_authored_layer(stage.GetRootLayer(), DATA / "lidar_wpm_howto_tile_lidars_1.usda")


def test_radar_wpm_dmat_howto_choose_parameters_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1-python]
    from pxr import Gf, Sdf

    radar = stage.DefinePrim("/generic_radar", "OmniRadar")
    radar.AddAppliedSchema("OmniSensorGenericRadarWpmDmatAPI")
    # Wavelength and coverage come from the selected device operating mode.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:waveLengthMm", Sdf.ValueTypeNames.Float, custom=False
    ).Set(3.9)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(50.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxAzAngDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(75.0)
    # Geometric sampling trades coverage against tracing cost.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:raysPerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(8.0)
    # Calibrate return strength against measurements; 1.0 is the default.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:powerFactor", Sdf.ValueTypeNames.Float, custom=False
    ).Set(1.0)
    # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-1-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "radar_wpm_dmat_howto_choose_parameters_1.usda"
    )


def test_radar_wpm_dmat_howto_choose_parameters_2(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2-python]
    from pxr import Gf, Sdf

    radar = stage.DefinePrim("/generic_radar", "OmniRadar")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:datacubeMode", Sdf.ValueTypeNames.Token, custom=False
    ).Set("WAVEFORM")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:waveformMode", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(0)
    # Each chirp repetition time must be at least the chirp duration.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:chirpDuration", Sdf.ValueTypeNames.Float, custom=False
    ).Set(2.5e-05)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:chirpBandwidth", Sdf.ValueTypeNames.Float, custom=False
    ).Set(3.75e08)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:chirpRepetitionTimeSequence",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([3.5e-05])
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:frequencyStepBetweenChirps",
        Sdf.ValueTypeNames.Float,
        custom=False,
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:supportFactor", Sdf.ValueTypeNames.Float, custom=False
    ).Set(1.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:slowTimeSamples", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(379)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:fastTimeSamples", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(625)
    # Transform lengths include zero padding; keep them at least as large as sample counts.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:slowTimePaddingSamples",
        Sdf.ValueTypeNames.UInt,
        custom=False,
    ).Set(512)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:fastTimePaddingSamples",
        Sdf.ValueTypeNames.UInt,
        custom=False,
    ).Set(1024)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:azimuthPaddingSamples", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(128)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:elevationPaddingSamples",
        Sdf.ValueTypeNames.UInt,
        custom=False,
    ).Set(32)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:windowSlowTime", Sdf.ValueTypeNames.Token, custom=False
    ).Set("RECT")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:windowFastTime", Sdf.ValueTypeNames.Token, custom=False
    ).Set("RECT")
    # The receiving aperture has 85 by 14 elements with the spacings below.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:apertureArrayAzimuthElements",
        Sdf.ValueTypeNames.UInt,
        custom=False,
    ).Set(85)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:apertureArrayElevationElements",
        Sdf.ValueTypeNames.UInt,
        custom=False,
    ).Set(14)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:apertureAzimuthElementSpacing",
        Sdf.ValueTypeNames.Float,
        custom=False,
    ).Set(0.00236)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:apertureElevationElementSpacing",
        Sdf.ValueTypeNames.Float,
        custom=False,
    ).Set(0.00332)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:apertureWindowAzimuth",
        Sdf.ValueTypeNames.Token,
        custom=False,
    ).Set("RECT")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:apertureWindowElevation",
        Sdf.ValueTypeNames.Token,
        custom=False,
    ).Set("RECT")
    # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-choose-parameters-2-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "radar_wpm_dmat_howto_choose_parameters_2.usda"
    )


def test_radar_wpm_dmat_howto_scan_configurations_1(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-radar-wpm-dmat-howto-scan-configurations-1-python]
    from pxr import Gf, Sdf

    radar = stage.DefinePrim("/generic_radar", "OmniRadar")
    radar.AddAppliedSchema("OmniSensorGenericRadarWpmDmatAPI")
    radar.AddAppliedSchema("OmniSensorGenericRadarWpmDmatScanCfgAPI:s002")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(50.0)
    # Geometric sampling trades coverage against tracing cost.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:raysPerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(10.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s002:maxRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(300.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s002:raysPerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(8.0)
    # [/snippet:doc-nonvisual-radar-wpm-dmat-howto-scan-configurations-1-python]
    _assert_authored_layer(
        stage.GetRootLayer(), DATA / "radar_wpm_dmat_howto_scan_configurations_1.usda"
    )


PUBLIC = Path(__file__).parents[3]


def _assert_example_snippet(actual, source, marker):
    text = source.read_text().split(f"# [snippet:{marker}]\n")[1].split(f"# [/snippet:{marker}]")[0]
    expected = Sdf.Layer.CreateAnonymous(".usda")
    expected.ImportFromString('#usda 1.0\ndef Xform "World" {\n' + textwrap.dedent(text) + "\n}\n")
    _assert_authored_layer(actual, expected)


def test_example_configure_acoustic_sensor(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-acoustic-sensor-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    acoustic = stage.DefinePrim("/World/Acoustic", "OmniAcoustic")
    acoustic.AddAppliedSchema("OmniSensorGenericAcousticWpmAPI")
    acoustic.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    acoustic.CreateAttribute(
        "omni:sensor:WpmAcoustic:azSpanDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(90.0)
    acoustic.CreateAttribute(
        "omni:sensor:WpmAcoustic:elSpanDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(60.0)
    acoustic.CreateAttribute(
        "omni:sensor:WpmAcoustic:raysPerDeg", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(3)
    acoustic.CreateAttribute(
        "omni:sensor:WpmAcoustic:traceTreeDepth", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    # Map sensor-local -Z to world +X and place the sensor 0.5 m above ground.
    acoustic.CreateAttribute("xformOp:transform", Sdf.ValueTypeNames.Matrix4d, custom=False).Set(
        Gf.Matrix4d(
            (0.0, -1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (-1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.5, 1.0)
        )
    )
    acoustic.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:transform"])
    # [/snippet:doc-nonvisual-example-configure-acoustic-sensor-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/acoustic/acoustic_example.usda",
        "configure-acoustic-sensor",
    )


def test_example_configure_acoustic_output(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-acoustic-output-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    render = stage.DefinePrim("/World/Render", "")

    products = stage.DefinePrim("/World/Render/Products", "")

    acoustic_product = stage.DefinePrim("/World/Render/Products/AcousticProduct", "RenderProduct")
    acoustic_product.CreateRelationship("camera", custom=False).SetTargets(["/World/Acoustic"])
    acoustic_product.CreateRelationship("orderedVars", custom=False).SetTargets(
        ["/World/Render/Vars/SignalWays"]
    )

    vars = stage.DefinePrim("/World/Render/Vars", "")

    signal_ways = stage.DefinePrim("/World/Render/Vars/SignalWays", "RenderVar")
    signal_ways.CreateAttribute(
        "sourceName", Sdf.ValueTypeNames.String, custom=False, variability=Sdf.VariabilityUniform
    ).Set("SignalWays")
    # [/snippet:doc-nonvisual-example-configure-acoustic-output-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/acoustic/acoustic_example.usda",
        "configure-acoustic-output",
    )


def test_example_configure_nonvisual_materials(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-nonvisual-materials-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    materials = stage.DefinePrim("/World/Materials", "Xform")

    asphalt = stage.DefinePrim("/World/Materials/Asphalt", "Material")
    asphalt.CreateAttribute(
        "omni:simready:nonvisual:base", Sdf.ValueTypeNames.Token, custom=False
    ).Set("asphalt")
    asphalt.CreateAttribute(
        "omni:simready:nonvisual:coating", Sdf.ValueTypeNames.Token, custom=False
    ).Set("none")
    asphalt.CreateAttribute(
        "omni:simready:nonvisual:attributes", Sdf.ValueTypeNames.TokenArray, custom=False
    ).Set(["none"])

    concrete = stage.DefinePrim("/World/Materials/Concrete", "Material")
    concrete.CreateAttribute(
        "omni:simready:nonvisual:base", Sdf.ValueTypeNames.Token, custom=False
    ).Set("concrete")
    concrete.CreateAttribute(
        "omni:simready:nonvisual:coating", Sdf.ValueTypeNames.Token, custom=False
    ).Set("none")
    concrete.CreateAttribute(
        "omni:simready:nonvisual:attributes", Sdf.ValueTypeNames.TokenArray, custom=False
    ).Set(["none"])
    # [/snippet:doc-nonvisual-example-configure-nonvisual-materials-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/acoustic/acoustic_example.usda",
        "configure-nonvisual-materials",
    )


def test_example_configure_lidar_sensor(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-lidar-sensor-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    lidar = stage.DefinePrim("/World/Lidar", "OmniLidar")
    lidar.AddAppliedSchema("OmniSensorGenericLidarCoreAPI")
    lidar.CreateAttribute(
        "omni:sensor:Core:elementsCoordsType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CARTESIAN")
    lidar.CreateAttribute(
        "omni:sensor:Core:includeInvalidPoints", Sdf.ValueTypeNames.Bool, custom=False
    ).Set(False)
    lidar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    lidar.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 0.0, 1.0)
    )
    lidar.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3, custom=False).Set(
        Gf.Vec3f(90.0, 0.0, -90.0)
    )
    lidar.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate", "xformOp:rotateXYZ"])
    # [/snippet:doc-nonvisual-example-configure-lidar-sensor-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/lidar/lidar_example.usda",
        "configure-lidar-sensor",
    )


def test_example_configure_lidar_pointcloud_output(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-lidar-pointcloud-output-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    render = stage.DefinePrim("/World/Render", "")

    products = stage.DefinePrim("/World/Render/Products", "")

    lidar_product = stage.DefinePrim("/World/Render/Products/LidarProduct", "RenderProduct")
    lidar_product.CreateRelationship("camera", custom=False).SetTargets(["/World/Lidar"])
    lidar_product.CreateRelationship("orderedVars", custom=False).SetTargets(
        ["/World/Render/Vars/PointCloud"]
    )

    vars = stage.DefinePrim("/World/Render/Vars", "")

    point_cloud = stage.DefinePrim("/World/Render/Vars/PointCloud", "RenderVar")
    point_cloud.CreateAttribute(
        "sourceName", Sdf.ValueTypeNames.String, custom=False, variability=Sdf.VariabilityUniform
    ).Set("PointCloud")
    point_cloud.CreateAttribute("channels", Sdf.ValueTypeNames.TokenArray, custom=False).Set(
        ["Coordinates", "Intensity", "Counts", "TimeOffsetNs"]
    )
    # [/snippet:doc-nonvisual-example-configure-lidar-pointcloud-output-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/lidar/lidar_example.usda",
        "configure-lidar-pointcloud-output",
    )


def test_example_configure_radar_sensor(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-radar-sensor-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    radar = stage.DefinePrim("/World/Radar", "OmniRadar")
    radar.AddAppliedSchema("OmniSensorGenericRadarWpmDmatAPI")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:elementsCoordsType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CARTESIAN")
    radar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    radar.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 0.0, 1.0)
    )
    radar.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3, custom=False).Set(
        Gf.Vec3f(90.0, 0.0, -90.0)
    )
    radar.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate", "xformOp:rotateXYZ"])
    # [/snippet:doc-nonvisual-example-configure-radar-sensor-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/radar/radar_example.usda",
        "configure-radar-sensor",
    )


def test_example_configure_radar_field_sensor(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-radar-field-sensor-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    radar = stage.DefinePrim("/World/Radar", "OmniRadar")
    radar.AddAppliedSchema("OmniSensorGenericRadarWpmDmatAPI")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:elementsCoordsType", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CARTESIAN")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:outputFrameOfReference", Sdf.ValueTypeNames.Token, custom=False
    ).Set("SENSOR")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:traceTreeDepth", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:cfarMode", Sdf.ValueTypeNames.Token, custom=False
    ).Set("2D")
    radar.CreateAttribute("omni:sensor:frameRate", Sdf.ValueTypeNames.Double2, custom=False).Set(
        Gf.Vec2d(10.0, 1.0)
    )
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:binsFromSpec", Sdf.ValueTypeNames.Bool, custom=False
    ).Set(False)
    # Geometric sampling trades coverage against tracing cost.
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:raysPerDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(8.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:rBins", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(112)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:vBins", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(161)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:azBins", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(12)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:elBins", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(2)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxRangeM", Sdf.ValueTypeNames.Float, custom=False
    ).Set(90.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxAzAngDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(75.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxElAngDeg", Sdf.ValueTypeNames.Float, custom=False
    ).Set(10.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:txAntennaGainMode", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CONSTANT")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:rxAntennaGainMode", Sdf.ValueTypeNames.Token, custom=False
    ).Set("CONSTANT")
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarRnT", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarRnG", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarVnT", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(1)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarVnG", Sdf.ValueTypeNames.UInt, custom=False
    ).Set(0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarMinVal", Sdf.ValueTypeNames.Float, custom=False
    ).Set(7e-17)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarOffset", Sdf.ValueTypeNames.Float, custom=False
    ).Set(1.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarNoiseMean", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:cfarNoiseSDev", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:rcsTuningCoefficients",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([-12.0, 150.0, 0.0])
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:azimuthRadNoiseMean", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:azimuthRadNoiseSDev", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:elevationRadNoiseMean",
        Sdf.ValueTypeNames.Float,
        custom=False,
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:elevationRadNoiseSDev",
        Sdf.ValueTypeNames.Float,
        custom=False,
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:rangeNoiseMean", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:rangeNoiseSDev", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:velocityNoiseMean", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:velocityNoiseSDev", Sdf.ValueTypeNames.Float, custom=False
    ).Set(0.0)
    radar.CreateAttribute(
        "omni:sensor:WpmDmat:scan:s001:maxVelMpsSequence",
        Sdf.ValueTypeNames.FloatArray,
        custom=False,
    ).Set([16.33])
    radar.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(0.0, 0.0, 1.0)
    )
    radar.CreateAttribute("xformOp:rotateXYZ", Sdf.ValueTypeNames.Float3, custom=False).Set(
        Gf.Vec3f(90.0, 0.0, -90.0)
    )
    radar.CreateAttribute(
        "xformOpOrder",
        Sdf.ValueTypeNames.TokenArray,
        custom=False,
        variability=Sdf.VariabilityUniform,
    ).Set(["xformOp:translate", "xformOp:rotateXYZ"])
    # [/snippet:doc-nonvisual-example-configure-radar-field-sensor-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/radar/radar_example_field.usda",
        "configure-radar-field-sensor",
    )


def test_example_configure_radar_field_output(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-configure-radar-field-output-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    render = stage.DefinePrim("/World/Render", "")

    products = stage.DefinePrim("/World/Render/Products", "")

    radar_product = stage.DefinePrim("/World/Render/Products/RadarProduct", "RenderProduct")
    radar_product.CreateRelationship("camera", custom=False).SetTargets(["/World/Radar"])
    radar_product.CreateRelationship("orderedVars", custom=False).SetTargets(
        ["/World/Render/Vars/PointCloud"]
    )

    camera_product = stage.DefinePrim("/World/Render/Products/CameraProduct", "RenderProduct")
    camera_product.CreateRelationship("camera", custom=False).SetTargets(["/World/PreviewCamera"])
    camera_product.CreateAttribute("resolution", Sdf.ValueTypeNames.Int2, custom=False).Set(
        Gf.Vec2i(960, 540)
    )
    camera_product.GetAttribute("resolution").SetVariability(Sdf.VariabilityVarying)
    camera_product.CreateAttribute(
        "omni:rtx:rendermode", Sdf.ValueTypeNames.Token, custom=False
    ).Set("RealTimePathTracing")
    camera_product.CreateRelationship("orderedVars", custom=False).SetTargets(
        ["/World/Render/Vars/LdrColor"]
    )

    vars = stage.DefinePrim("/World/Render/Vars", "")

    point_cloud = stage.DefinePrim("/World/Render/Vars/PointCloud", "RenderVar")
    point_cloud.CreateAttribute(
        "sourceName", Sdf.ValueTypeNames.String, custom=False, variability=Sdf.VariabilityUniform
    ).Set("PointCloud")
    point_cloud.CreateAttribute("channels", Sdf.ValueTypeNames.TokenArray, custom=False).Set(
        ["Coordinates", "Counts", "RCS", "RadialVelocityMs"]
    )

    ldr_color = stage.DefinePrim("/World/Render/Vars/LdrColor", "RenderVar")
    ldr_color.CreateAttribute(
        "sourceName", Sdf.ValueTypeNames.String, custom=False, variability=Sdf.VariabilityUniform
    ).Set("LdrColor")
    # [/snippet:doc-nonvisual-example-configure-radar-field-output-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/python/radar/radar_example_field.usda",
        "configure-radar-field-output",
    )


def test_example_radar_pointcloud(tmp_path):
    stage = _stage_with_profiles(tmp_path)
    # [snippet:doc-nonvisual-example-radar-pointcloud-python]
    from pxr import Gf, Sdf

    world = stage.DefinePrim("/World", "Xform")

    render = stage.DefinePrim("/World/Render", "")

    products = stage.DefinePrim("/World/Render/Products", "")

    radar_product = stage.DefinePrim("/World/Render/Products/RadarProduct", "RenderProduct")
    radar_product.CreateRelationship("camera", custom=False).SetTargets(["/World/Radar"])
    radar_product.CreateRelationship("orderedVars", custom=False).SetTargets(
        ["/World/Render/Vars/PointCloud"]
    )

    vars = stage.DefinePrim("/World/Render/Vars", "")

    point_cloud = stage.DefinePrim("/World/Render/Vars/PointCloud", "RenderVar")
    point_cloud.CreateAttribute(
        "sourceName", Sdf.ValueTypeNames.String, custom=False, variability=Sdf.VariabilityUniform
    ).Set("PointCloud")
    point_cloud.CreateAttribute("channels", Sdf.ValueTypeNames.TokenArray, custom=False).Set(
        ["Coordinates", "Counts", "RCS", "RadialVelocityMs"]
    )
    # [/snippet:doc-nonvisual-example-radar-pointcloud-python]
    _assert_example_snippet(
        stage.GetRootLayer(),
        PUBLIC / "examples/c/radar/radar_example.usda",
        "configure-radar-pointcloud-output",
    )
