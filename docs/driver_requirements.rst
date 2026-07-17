.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

Driver Requirements
===================

ovrtx runtime validation requires an NVIDIA RTX-capable GPU and a supported NVIDIA driver.

Last updated: 2026-05-21.

The tables below list the minimum validated NVIDIA driver versions for ovrtx runtime validation by host OS, GPU generation, and GPU type. Drivers older than these versions are not supported. Newer drivers can work, but the versions below are the validated baseline.

For local workstations, download drivers from the `NVIDIA driver download page <https://www.nvidia.com/Download/index.aspx>`_. For cloud provider virtual machines, use the GPU driver supplied by the cloud provider for that instance type.

Blackwell
---------

.. tab-set::

   .. tab-item:: Linux

      .. list-table::
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           - 570.169
           - 580.95.05
           - 595.58.03
         * - Workstation
           - 570.169
           - 580.95.05
           - 595.58.03
         * - Data Center
           - Not listed
           - 580.95.05
           - 595.58.03

   .. tab-item:: Windows

      .. list-table::
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           - Not listed
           - 581.42
           - 595.97
         * - Workstation
           - 573.42
           - 581.42
           - 595.97
         * - Data Center
           - Not listed
           - 581.42
           - 595.97

Ada, Ampere, and Turing
-----------------------

.. tab-set::

   .. tab-item:: Linux

      .. list-table::
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           - 570.169
           - 580.95.05
           - 595.58.03
         * - Workstation
           - 570.169
           - 580.95.05
           - 595.58.03
         * - Data Center
           - 570.158.01
           - 580.95.05
           - 595.58.03

   .. tab-item:: Windows

      .. list-table::
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           - Not listed
           - 581.42
           - 595.97
         * - Workstation
           - 573.42
           - 581.42
           - 595.97
         * - Data Center
           - 573.39
           - 581.42
           - 595.97

Known Driver Notes
------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Driver or platform
     - Note
   * - Linux 595.58.03 on Microsoft Azure RTX Pro 6000 Preview
     - Not compatible with Kit versions older than 109.0.5 and 110.1.0.
   * - Windows 11 KB5074109, January 13, 2026 security update
     - Vulkan API use requires an NVIDIA driver with the relevant fix. On the R580 branch, use 582.41 or newer. On R595, use 595.97.
   * - Windows R560, R570, R575
     - DirectX 12 scenes with very large instance counts may show performance degradation. Fixed versions include 576.80, 573.42, and 573.39.
   * - Windows 11 24H2 R570, R575
     - Multi-GPU systems with at least one Blackwell GPU may crash. Fixed versions include 576.80 and 573.42.
   * - Linux 570.144 and older
     - Some Kit apps may crash during driver shader compilation while loading scenes. Fixed in 575.64.
   * - Windows R550, R560, R570, R575
     - Omniverse WebRTC Streaming may freeze when Windows Hardware-accelerated GPU scheduling is enabled.
   * - 535.256 and newer on Vulkan
     - Vulkan may report these versions incorrectly and cause driver compatibility checks to fail.
