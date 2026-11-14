# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

# Give a shared-loader executable its own plugin root. Link large subdirectories
# to the SDK, but copy root files so adding OVStage cannot modify the OVRTX SDK.
param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Destination,
    [string]$PopulationPlugin
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Plugin source directory is missing: $Source"
}
if ($PopulationPlugin -and -not (Test-Path -LiteralPath $PopulationPlugin -PathType Leaf)) {
    throw "OVStage population plugin is missing: $PopulationPlugin"
}
$root = Get-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
if ($root -and ($root.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    # Delete only the old junction, never its package contents.
    $root.Delete()
}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
foreach ($entry in Get-ChildItem -LiteralPath $Source -Force) {
    $target = Join-Path $Destination $entry.Name
    if ($entry.PSIsContainer) {
        $old = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
        if ($old) {
            if (-not ($old.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw "Expected a directory link at $target; remove it and retry"
            }
            $old.Delete()
        }
        New-Item -ItemType Junction -Path $target -Target $entry.FullName | Out-Null
    } else {
        Copy-Item -LiteralPath $entry.FullName -Destination $target -Force
    }
}
if ($PopulationPlugin) {
    Copy-Item -LiteralPath $PopulationPlugin -Destination $Destination -Force
}
