.. SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: LicenseRef-NvidiaProprietary
..
.. NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
.. property and proprietary rights in and to this material, related
.. documentation and any modifications thereto. Any use, reproduction,
.. disclosure or distribution of this material and related documentation
.. without an express license agreement from NVIDIA CORPORATION or
.. its affiliates is strictly prohibited.

.. _driver-requirements:

Hardware & Driver Requirements
==============================

This page lists the minimum and recommended hardware and supported NVIDIA
drivers for ovrtx. Size an ovrtx deployment for its actual
scenes, sensors, output resolution, and frame rate.

Hardware
--------

.. list-table:: Minimum and recommended configurations
   :class: compact-table
   :header-rows: 1
   :widths: 20 25 10 25 20

   * - Configuration
     - CPU
     - RAM
     - GPU
     - Storage
   * - Minimum
     - Intel i7/i9 or AMD Ryzen
     - 16 GB
     - GeForce RTX 3070
     - 250 GB
   * - Recommended x86_64 workstation
     - Current Xeon, Core i9, Threadripper, or Ryzen; 16+ cores
     - 128–256 GB
     - RTX Pro 6000 Blackwell
     - NVMe, 1 TB or more
   * - Recommended x86_64 server
     - Current Xeon or EPYC; 64+ cores, 3+ GHz base
     - 1–2 TB
     - 8 × RTX Pro 6000 Blackwell Server Edition; 768 GB total GPU memory
     - Scale to workload
   * - ARM64 / aarch64
     - ARM64
     - 128–256 GB
     - RTX Pro 6000 Blackwell
     - NVMe, 1 TB or more

ovrtx supports Windows 11 and Ubuntu 22.04/24.04 on x86_64, and Ubuntu
22.04/24.04 on ARM64. Windows on Arm is supported with the Windows x86_64
package via emulation. RAM depends on workload and OS.

Renderer Feature Support
------------------------

Feature availability depends on GPU architecture and graphics API.
Non-RTX GPUs carry no support guarantee.

.. list-table:: Renderer feature support by GPU architecture
   :class: compact-table
   :header-rows: 1
   :widths: 20 8 12 12 12 12 12 12

   * - GPU architecture
     - Compute capability
     - DLSS Ray Reconstruction [#ray-reconstruction]_
     - DLSS Frame Generation
     - OptiX Denoiser
     - Shader Execution Reordering
     - Opacity Micro-Map
     - Motion BVH
   * - Blackwell (RTX) Pro
     - 12.0
     - Yes [#blackwell-linux]_
     - Yes
     - Yes
     - Yes (DX12)
     - Yes
     - Yes (Vulkan)
   * - Blackwell B200/B300
     - 10.0
     - Yes [#blackwell-linux]_
     - No
     - Yes
     - No
     - No
     - No
   * - Hopper H100/H200/H800
     - 9.0
     - No
     - No
     - Yes
     - No
     - No
     - No
   * - Ada Lovelace
     - 8.9
     - Yes
     - Yes
     - Yes
     - Yes (DX12)
     - Yes
     - Yes (Vulkan)
   * - Ampere (RTX)
     - 8.6
     - Yes
     - No
     - Yes
     - No
     - No
     - Yes (Vulkan)
   * - Ampere A100/A30/A800
     - 8.0
     - No
     - No
     - Yes
     - No
     - No
     - No
   * - Turing
     - 7.5
     - Yes
     - No
     - Yes
     - No
     - No
     - No

.. [#ray-reconstruction] Without DLSS Ray Reconstruction, RTX Real-Time images can be significantly noisy.
.. [#blackwell-linux] On Linux, Blackwell DLSS Ray Reconstruction requires a runtime based on Kit 106.5.3 or newer.

Tesla, Fermi, Kepler, Maxwell, Pascal, and Volta architectures are unsupported.

Drivers
-------

ovrtx runtime validation requires an NVIDIA RTX-capable GPU and a supported NVIDIA driver.

These are the supported NVIDIA driver versions for ovrtx, grouped by OS, GPU generation, and GPU type. Newer releases may work without having completed validation; also check the platform-specific notes below. An empty cell means there is no validated version for that combination.

For local workstations, download drivers from the `NVIDIA driver download page <https://www.nvidia.com/Download/index.aspx>`_.

.. important::

   For deployments on cloud service providers (CSPs), obtain GPU drivers
   directly from the provider hosting your virtual machine:

   * `Amazon Web Services <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html>`_
   * `Microsoft Azure <https://learn.microsoft.com/en-us/azure/virtual-machines/windows/n-series-driver-setup>`_
   * `Google Cloud Platform <https://docs.cloud.google.com/compute/docs/gpus/install-drivers-gpu>`_

Blackwell
~~~~~~~~~

.. tab-set::

   .. tab-item:: Linux

      .. list-table::
         :class: compact-table
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           - |linux-570|
           - |linux-580|
           - |linux-595|
         * - Workstation
           - |linux-570|
           - |linux-580|
           - |linux-595|
         * - Data Center
           -
           - |linux-580|
           - |linux-595|

   .. tab-item:: Windows

      .. list-table::
         :class: compact-table
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           -
           - |windows-geforce-580|
           - |windows-geforce-595|
         * - Workstation
           - |windows-workstation-570|
           - |windows-workstation-580|
           - |windows-workstation-595|
         * - Data Center
           -
           - |windows-datacenter-580|
           - |windows-datacenter-595|

Ada, Ampere, and Turing
~~~~~~~~~~~~~~~~~~~~~~~

.. tab-set::

   .. tab-item:: Linux

      .. list-table::
         :class: compact-table
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           - |linux-570|
           - |linux-580|
           - |linux-595|
         * - Workstation
           - |linux-570|
           - |linux-580|
           - |linux-595|
         * - Data Center
           - |linux-datacenter-570|
           - |linux-580|
           - |linux-595|

   .. tab-item:: Windows

      .. list-table::
         :class: compact-table
         :header-rows: 1
         :widths: 25 25 25 25

         * - GPU type
           - R570 Production Branch
           - R580 Production Branch
           - R595 Production Branch
         * - GeForce
           -
           - |windows-geforce-580|
           - |windows-geforce-595|
         * - Workstation
           - |windows-workstation-570|
           - |windows-workstation-580|
           - |windows-workstation-595|
         * - Data Center
           - |windows-datacenter-570|
           - |windows-datacenter-580|
           - |windows-datacenter-595|

Known Driver Notes
~~~~~~~~~~~~~~~~~~

.. list-table::
   :class: compact-table
   :header-rows: 1
   :widths: 35 65

   * - Driver or platform
     - Note
   * - Linux aarch64 R580, R595
     - Use 580.173.02 or 595.84, or newer within the respective branch, for OpenGL interop and Pixar Hydra engine crash fixes.
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

.. |linux-570| replace:: `570.169 <https://www.nvidia.com/en-us/drivers/details/247720/>`__
.. |linux-580| replace:: `580.95.05 <https://www.nvidia.com/en-us/drivers/details/254665/>`__
.. |linux-595| replace:: `595.58.03 <https://www.nvidia.com/en-us/drivers/details/265870/>`__
.. |linux-datacenter-570| replace:: `570.158.01 <https://www.nvidia.com/en-us/drivers/details/247702/>`__
.. |windows-geforce-580| replace:: `581.42 <https://www.nvidia.com/en-us/drivers/details/257133/>`__
.. |windows-geforce-595| replace:: `595.97 <https://www.nvidia.com/en-us/drivers/details/265875/>`__
.. |windows-workstation-570| replace:: `573.42 <https://www.nvidia.com/en-us/drivers/details/247852/>`__
.. |windows-workstation-580| replace:: `581.42 <https://www.nvidia.com/en-us/drivers/details/254655/>`__
.. |windows-workstation-595| replace:: `595.97 <https://www.nvidia.com/en-us/drivers/details/265877/>`__
.. |windows-datacenter-570| replace:: `573.39 <https://www.nvidia.com/en-us/drivers/details/247715/>`__
.. |windows-datacenter-580| replace:: `581.42 <https://www.nvidia.com/en-us/drivers/details/254614/>`__
.. |windows-datacenter-595| replace:: `595.97 <https://www.nvidia.com/en-us/drivers/details/266131/>`__
