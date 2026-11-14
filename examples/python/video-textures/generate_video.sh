#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

set -euo pipefail

cd "$(dirname "$0")"

# Generate a four-second, seekable H.265/HEVC Main Profile clip. The moving ball
# and stream-time overlay make incorrect frame selection immediately visible.
gst-launch-1.0 -e \
    videotestsrc num-buffers=40 pattern=ball animation-mode=frames motion=wavy \
        background-color=4279247935 foreground-color=4294943264 \
    ! video/x-raw,width=640,height=360,framerate=10/1 \
    ! timeoverlay time-mode=stream-time text="VIDEO TIME " \
        valignment=top halignment=left shaded-background=true font-desc="Sans Bold 28" \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! x265enc speed-preset=ultrafast tune=zerolatency bitrate=1200 \
        key-int-max=10 option-string=bframes=0 \
    ! h265parse config-interval=-1 \
    ! video/x-h265,stream-format=hvc1,alignment=au \
    ! mp4mux faststart=true \
    ! filesink location=video_texture_h265.mp4
