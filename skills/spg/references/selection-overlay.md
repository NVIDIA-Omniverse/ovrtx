<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
-->

# Custom selection overlay reference

The parent SPG skill contains tested kernel, launcher and graph snippets for this example.

The example consumes `SelectionState` (output-resolution RGBA16_UINT coverage states)
and `LdrColor`. Each state stores group in bits 0–7 and visible/hidden in bit 8;
zero means background. SPG owns width, shape, colors, dashes, boundaries and fill.
Requesting `SelectionState` suppresses the native overlay.
The example requires the SDK revision that introduces the SelectionState producer.
