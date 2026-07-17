.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Non-Visual Sensors
==================

Non-visual sensors in ovrtx produce structured sensor data rather than camera
images. Lidar and radar commonly expose composite ``PointCloud`` RenderVars with
named tensors such as coordinates, counts, intensity, RCS, radial velocity, and
time offsets. Non-visual material labels let those sensors model material-facing
return behavior independently of visual shading.

For shared RenderProduct and RenderVar concepts, refer to :doc:`configuration` and
:doc:`sensor_outputs`.

.. toctree::
   :maxdepth: 1

   lidar
   radar
   pointclouds
   nonvisual_materials
