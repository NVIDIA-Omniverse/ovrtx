# [snippet:doc-calibration-reference-python]
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateNew("_out/scene.usda")
UsdGeom.Xform.Define(stage, "/World")
camera = UsdGeom.Camera.Define(stage, "/World/Camera")
# The asset path is relative to scene.usda; defaultPrim selects the Camera.
camera.GetPrim().GetReferences().AddReference("calibrated_camera.usda")
stage.GetRootLayer().Save()
# [/snippet:doc-calibration-reference-python]
