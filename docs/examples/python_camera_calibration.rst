.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _sensors-recipes-camera-intrinsic-calibration:

Python: Camera calibration
==========================

Fit a camera model from checkerboard photographs and save the calibration as a
USD Camera. The script estimates a 3×3 camera matrix *K* (focal lengths and
principal point) and a distortion vector *D*, then writes them to the matching
OpenCV lens-distortion schema.

Calibration measures projection differences that can affect reprojection,
stereo depth and synthetic images: unequal focal lengths, an off-center principal
point, and barrel or pincushion distortion.

.. _sensors-recipes-calibration-boundary:

What Calibration Controls
-------------------------

Intrinsics control projection: where scene points appear and how straight lines
curve in the image. They do not change the :doc:`render mode <../sensors/cameras/render_modes>`
or :doc:`available outputs <../sensors/cameras/outputs>`.

The :doc:`Camera generic core model <../sensors/visual/camera_core/index>` simulates
sensor response and image processing after rendering. It can share the Camera
prim with a lens model; each uses its own attributes.

Set Up the Example
------------------

The example project is in ``examples/python/camera-calibration``. It includes
``main.py``, ``pyproject.toml``, ``uv.lock`` and the eight photographs in
``input_images/``. No renderer or GPU is required.

From the SDK root, enter the example directory:

.. code-block:: bash

   cd examples/python/camera-calibration

``uv run`` creates the project environment and installs the locked dependencies:
OpenCV, NumPy and USD. Python 3.10–3.14 is supported.

.. _sensors-recipes-calibration-opencv-pin:

The project requires ``opencv-python>=4.8,<5``. The fisheye workflow was validated
with the locked OpenCV 4.14.0.94 and the supplied photographs.

.. _sensors-recipes-calibration-example-images:

The Example Photographs
-----------------------

The eight supplied fisheye photographs are 1920×1536 and show a board with a
20×14 inner-corner grid. They are already in ``input_images/``:

.. figure:: ../img/sensors/camera/calibration-inputs.avif
   :alt: Eight fisheye photographs of a checkerboard at different positions and angles
   :width: 100%

   The input photographs, labeled by filename suffix.

For your own photographs, use one image resolution and vary the board's angle,
distance and position across the frame. Pass the folder with ``--images`` and
set ``--pattern`` to your board's inner-corner grid. Use ``--fisheye`` only for a
fisheye lens.

The commands below use ``--fisheye --pattern 20x14`` for the example photographs.

Choosing a lens model
---------------------

ovrtx provides schemas matching both OpenCV's pinhole and fisheye models:
``OmniLensDistortionOpenCvPinholeAPI`` and
``OmniLensDistortionOpenCvFisheyeAPI``. Use the pinhole model for conventional
lenses and the fisheye model for fisheye lenses.

See :ref:`OpenCV pinhole <sensors-cameras-lens-calibration-pinhole>` and
:ref:`OpenCV fisheye <sensors-cameras-lens-calibration-fisheye>` for schema
attributes, and :ref:`calibration resolution
<sensors-cameras-lens-calibration-resolution>` for rendering at a different
resolution. The script does not produce lookup-table or omni-directional stereo
calibrations.

Run It
------

.. code-block:: bash

   uv run main.py --fisheye --pattern 20x14 --output-usd ./_out/calibrated_camera.usda

.. list-table::
   :header-rows: 1
   :widths: 26 22 52

   * - Flag
     - Default
     - What it does
   * - ``--images DIR``
     - ``input_images/`` beside the script
     - The folder of checkerboard photographs. Files ending ``.png``, ``.jpg`` or
       ``.jpeg``, in lower or upper case, are picked up.
   * - ``--pattern COLSxROWS``
     - ``20x14``
     - The inner-corner grid of the board.
   * - ``--fisheye``
     - off, so pinhole
     - Solve the four-coefficient fisheye model instead of the pinhole one, and
       write the fisheye schema.
   * - ``--rational``
     - off
     - Pinhole only: solve the eight-coefficient rational model instead of the
       five-coefficient model. Cannot be combined with ``--fisheye``.
   * - ``--output-usd PATH``
     - ``./_out/calibrated_camera.usda``
     - Where to write the camera. Missing parent directories are created.

.. _sensors-recipes-calibration-pattern-inner-corners:

Count inner corners, not squares: a board of *N* × *M* squares has
(*N* - 1) × (*M* - 1) inner corners. A 21×15-square board needs
``--pattern 20x14``. A mismatched pattern prevents detection; the script reports
skipped photographs and stops if too few boards are detected.

What the Script Does
--------------------

Detect corners
^^^^^^^^^^^^^^

Find the checkerboard grid in each grayscale photograph and refine its corner
positions to sub-pixel accuracy. Skip images where the grid is not detected;
collect the remaining image points and corresponding board coordinates for fitting.

.. literalinclude:: ../../examples/python/camera-calibration/main.py
   :language: python
   :start-after: # [snippet:doc-calibration-detect-corners]
   :end-before: # [/snippet:doc-calibration-detect-corners]
   :dedent:

Fit the model
^^^^^^^^^^^^^

Fit the selected OpenCV model to the collected points. The solver returns the
camera matrix ``K``, distortion vector ``D`` and reprojection RMS. The pinhole
path optionally enables the rational model; the fisheye helper tries several
initial focal lengths.

.. literalinclude:: ../../examples/python/camera-calibration/main.py
   :language: python
   :start-after: # [snippet:doc-calibration-solve]
   :end-before: # [/snippet:doc-calibration-solve]
   :dedent:

Write the camera attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Apply the selected lens-distortion schema to the USD Camera and write the solved
parameters as attributes in its namespace. Store the calibration image size so
ovrtx can scale the intrinsics to the RenderProduct resolution.

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../examples/python/camera-calibration/doc_snippets/camera_attributes.usda
         :language: usda
         :start-after: # [snippet:doc-calibration-write-camera-usda]
         :end-before: # [/snippet:doc-calibration-write-camera-usda]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../examples/python/camera-calibration/main.py
         :language: python
         :start-after: # [snippet:doc-calibration-write-camera]
         :end-before: # [/snippet:doc-calibration-write-camera]
         :dedent:

.. _sensors-recipes-calibration-min-images:

The script requires at least three photographs with detected boards. Use more,
with varied angles, distances and positions, to cover the image rather than
concentrating corners near its center.

.. _sensors-recipes-calibration-fisheye-seeds:

The fisheye solver tries initial focal lengths of 0.3, 0.4, 0.5, 0.6, 0.8 and
1.0 times the longer image dimension. It discards attempts that raise an error
or return a non-finite RMS, then keeps the lowest RMS. If all six fail, it stops.

.. _sensors-recipes-calibration-rms:

Reprojection RMS measures the residual between detected and projected corners,
in pixels. Below about 0.5 pixels is a useful rule of thumb, not a guarantee of
accuracy. The script reports and stores the RMS but does not enforce a threshold;
a poor fit still produces a file.

.. _sensors-recipes-calibration-d-layout:

The script maps OpenCV's distortion vector to named attributes. For pinhole,
the tangential terms precede the third radial term; preserve this ordering if
copying a vector by hand.

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Solve
     - OpenCV *D*
     - Attributes written
   * - Pinhole, five coefficients
     - ``[k1, k2, p1, p2, k3]``
     - ``k1``, ``k2``, ``p1``, ``p2`` and ``k3`` from the solve; every other
       coefficient of the schema is written as zero.
   * - Pinhole, rational
     - ``[k1, k2, p1, p2, k3, k4, k5, k6]``
     - ``k1`` through ``k6`` and ``p1``, ``p2`` from the solve. ``s1`` through
       ``s4`` are always written as zero, because the script never asks for the
       thin-prism solve that would produce them.
   * - Fisheye
     - ``[k1, k2, k3, k4]``
     - ``k1`` through ``k4``. The fisheye schema has no tangential or thin-prism
       terms.

The Camera It Writes
--------------------

The output contains a Camera prim with the selected OpenCV schema, solved
intrinsics and calibration image size. Attribute definitions, types and defaults
are listed under :ref:`OpenCV pinhole
<sensors-cameras-lens-calibration-pinhole>` and :ref:`OpenCV fisheye
<sensors-cameras-lens-calibration-fisheye>` in
:doc:`Lens Calibration <../sensors/cameras/lens_calibration>`.

The script also writes two custom attributes: ``calibration:model`` records the
model and ``calibration:reprojectionRmsPixels`` records the fit error. These are
metadata for tracing the calibration; they do not affect rendering.

.. _sensors-recipes-calibration-model-selector:

The script relies on the applied schema's ``omni:lensdistortion:model`` fallback
rather than authoring the selector. The lens-distortion schemas must be registered
when the stage is read for that fallback to resolve. Lens Calibration's examples
author the selector explicitly.

.. _sensors-recipes-calibration-nominal-body:

The script also writes standard camera attributes for plain USD viewers:

- For pinhole, it derives focal length, apertures and offsets from the solve.
  ``focalLength`` is set to *fx* and the horizontal aperture to the image width
  to reproduce the field of view.
- For fisheye, these are nominal placeholders; the calibrated projection is
  carried by the lens-distortion schema.

These focal-length values are not physical lens measurements. The script leaves
``fStop`` unauthored, so depth of field is off. Before enabling it, set physical
focal length and aperture values; see :doc:`../sensors/cameras/lens_calibration` for the
attributes depth of field uses. The output layer is Y-up.

Check the Result
----------------

The run reports per photograph as it goes, then prints a summary:

.. code-block:: text

      [ok]   corners found: Internal_reference_calibration_1.png
      [skip] no 20x14 board: some_other_photo.png

    Calibrating from <n> images at 1920x1536 ...

    ============================================================
    Camera intrinsic calibration
    ============================================================
    Model:              fisheye (k1..k4)
    Resolution:         1920 x 1536
    Focal length (px):  fx=...  fy=...
    Principal point:    cx=...  cy=...
    Distortion coeffs:  [...]
    Reprojection RMS:   ... px
    Images used:        ...  (failed: ...)
    ============================================================

    USD camera written: ./_out/calibrated_camera.usda

Check the following:

- **Images used:** compare with the number supplied. If many were skipped, check
  the pattern, focus and board visibility before changing solver settings.
- **Reprojection RMS:** assess the fit using the
  :ref:`guidance above <sensors-recipes-calibration-rms>`.
- **Principal point:** usually near the image center (about 960, 768 for the
  example images). A large offset warrants checking the solve.
- **Written USD:** check that ``prepend apiSchemas`` names the expected schema
  and ``imageSize`` matches the calibration photographs.

Results can vary with OpenCV version and, for fisheye, the selected starting
point. Compare with a tolerance rather than expecting identical final digits.

Potential issues
----------------

When using your own images with this script, check for the following:

- ``no images found in <dir>`` — the folder is empty or holds files the script does
  not glob. Only ``.png``, ``.jpg`` and ``.jpeg`` are read.
- ``need >=3 images with a detected board, got <n>`` — the boards were not detected,
  and the count is how many were. Check ``--pattern`` first; see
  :ref:`inner corners <sensors-recipes-calibration-pattern-inner-corners>`. Blur,
  glare, a partially visible board, or a board too small in the frame do the same
  thing to individual photographs. The script names each skipped photograph.
- ``image size mismatch: <name> is WxH, expected WxH`` — the folder mixes
  resolutions. Intrinsics are in pixels, so photographs from two resolutions cannot
  be solved together. Split them and calibrate each set separately.
- ``fisheye calibration failed to converge for any focal seed`` — every one of the
  six starting guesses diverged. Check that the photographs really are fisheye and
  that the pattern is right; if they are and it still fails, check the OpenCV
  version against :ref:`the pin <sensors-recipes-calibration-opencv-pin>`.
- ``--rational is only valid for pinhole calibration`` — the rational model is a
  pinhole-only refinement and was passed together with ``--fisheye``. Drop one of
  the two flags.
- The calibration succeeds but the rendered image is not distorted — the camera prim
  is not carrying a resolvable
  :ref:`model selector <sensors-recipes-calibration-model-selector>`, or the
  attributes were copied under the wrong namespace. ``opencvFisheye`` and
  ``opencvPinhole`` attribute names are not interchangeable, and a value authored
  under the namespace the camera is not using is an attribute nothing reads.

Use the Calibrated Camera in a Scene
------------------------------------

Reference the generated Camera prim into your scene. The calibration script sets
it as the asset's ``defaultPrim``, so the reference needs only the file path.
This creates ``_out/scene.usda`` with the camera at ``/World/Camera``:

.. tab-set::

   .. tab-item:: USDA
      :sync: usda

      .. literalinclude:: ../../examples/python/camera-calibration/doc_snippets/reference_camera.usda
         :language: usda
         :start-after: # [snippet:doc-calibration-reference-usda]
         :end-before: # [/snippet:doc-calibration-reference-usda]
         :prepend: #usda 1.0

   .. tab-item:: USD Python
      :sync: python

      .. literalinclude:: ../../examples/python/camera-calibration/doc_snippets/reference_camera.py
         :language: python
         :start-after: # [snippet:doc-calibration-reference-python]
         :end-before: # [/snippet:doc-calibration-reference-python]
         :dedent:

Set the referenced camera's pose in your scene and point the RenderProduct's
``camera`` relationship at it. The lens parameters remain in the referenced
asset. See :doc:`../sensors/common/output_configuration` for connecting the
camera to a RenderProduct.

For each calibration photograph, reproduce the camera and checkerboard poses in
the scene and compare a render with the photograph. Check the corner positions
and line curvature across the frame.

.. image:: ../img/sensors/camera/sensors_camera_intrinsic_calibration_sim_grid.avif
   :alt: A grid of simulated checkerboard views rendered through the calibrated fisheye camera, one tile per calibration pose.
   :width: 100%

The grid uses the calibration solved from the example photographs, with one tile
per calibration pose, to compare simulated and photographed distortion.

Related
-------

- :doc:`../sensors/cameras`
- :doc:`../sensors/cameras/lens_calibration`
- :doc:`../sensors/cameras/usd_camera_attributes`
- :doc:`../sensors/cameras/outputs`
