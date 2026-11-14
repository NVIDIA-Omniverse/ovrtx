#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Archive release documentation once and assemble versioned Pages deployments."""

import html
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


def main():
    """Keep the build matrix and published navigation derived from one manifest."""
    command = sys.argv[1]
    repository = os.environ.get("GITHUB_REPOSITORY", "NVIDIA-Omniverse/ovrtx")
    owner, name = repository.split("/")
    base_url = f"https://{owner.lower()}.github.io/{name}/"

    if command == "discover":
        # Tags can arrive before their release. Only published releases
        # belong on the site; pushes alone must never publish documentation.
        tags = subprocess.check_output(["git", "tag", "--list"], text=True).splitlines()
        tags = [tag for tag in tags if re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", tag)]
        tags.sort(key=lambda tag: tuple(map(int, tag[1:].split("."))), reverse=True)
        if not tags:
            raise SystemExit("No release tags found; refusing to publish an empty site")

        # Listing releases must succeed: authentication/network failures must never
        # be interpreted as a missing archive and trigger historical rebuilds.
        pages = json.loads(subprocess.check_output([
            "gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases?per_page=100",
        ], text=True))
        releases = {release["tag_name"]: release for page in pages for release in page}
        entries = []
        for tag in tags:
            release = releases.get(tag)
            if not release or release["draft"]:
                continue
            version = tag[1:]
            asset_name = f"ovrtx-docs-{version}.tar.gz"
            assets = release["assets"]
            asset = next((asset for asset in assets if asset["name"] == asset_name), None)
            if release.get("immutable") and asset is None:
                raise SystemExit(f"Immutable release {tag} has no docs archive; assets cannot be added")
            if asset and asset["state"] != "uploaded":
                raise SystemExit(f"Incomplete release asset: {tag}/{asset_name}")
            entries.append({
                "ref": tag, "version": version,
                "sha": subprocess.check_output(["git", "rev-parse", f"{tag}^{{commit}}"], text=True).strip(),
                "asset": asset_name, "reuse": asset is not None,
            })
        if not entries:
            raise SystemExit("No published releases found; refusing to publish an empty site")
        Path("versions.json").write_text(json.dumps(entries, indent=2) + "\n")
        print("matrix=" + json.dumps({"include": entries}))

    elif command == "pack":
        # Capture the exact output and tool versions once, before site assembly.
        source, output = map(Path, sys.argv[2:4])
        version = sys.argv[4]
        entry = next(entry for entry in json.loads(Path("versions.json").read_text()) if entry["version"] == version)
        if not (source / "index.html").is_file():
            raise SystemExit(f"Missing documentation: {source}")
        metadata = {
            "repository": repository, "version": version, "source_sha": entry["sha"],
            "publisher_sha": subprocess.check_output([
                "git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD",
            ], text=True).strip(),
            "python": sys.version,
            "packages": {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()},
            "doxygen": subprocess.check_output(["doxygen", "--version"], text=True).strip(),
            "graphviz": subprocess.check_output(["dot", "-V"], stderr=subprocess.STDOUT, text=True).strip(),
        }
        (source / "docs-build.json").write_text(json.dumps(metadata, indent=2) + "\n")
        # Exclusive creation also prevents accidental local replacement.
        with tarfile.open(output, "x:gz") as archive:
            archive.add(source, arcname=".")

    elif command == "unpack":
        # Reject unexpected archives and changed tags instead of rebuilding silently.
        archive_path, destination = map(Path, sys.argv[2:4])
        version = sys.argv[4]
        entry = next(entry for entry in json.loads(Path("versions.json").read_text()) if entry["version"] == version)
        destination.mkdir(parents=True, exist_ok=False)
        with tarfile.open(archive_path, "r:gz") as archive:
            if any(not (member.isfile() or member.isdir()) for member in archive.getmembers()):
                raise SystemExit("Docs archive contains links or special files")
            archive.extractall(destination, filter="data")
        metadata = json.loads((destination / "docs-build.json").read_text())
        if (metadata["repository"], metadata["version"], metadata["source_sha"]) != (repository, version, entry["sha"]):
            raise SystemExit(f"Docs archive provenance does not match {entry['ref']}")
        if not (destination / "index.html").is_file():
            raise SystemExit("Docs archive is missing index.html")

    elif command == "configure":
        # Append only publishing settings; retain the tag's source and extensions.
        source = Path(sys.argv[2])
        version = sys.argv[3]
        entries = json.loads(Path("versions.json").read_text())
        if version not in {entry["version"] for entry in entries}:
            raise SystemExit(f"Version absent from build manifest: {version}")
        with (source / "docs/conf.py").open("a") as config:
            config.write(f'''

# CI publishing overlay: this checkout is disposable.
html_baseurl = {base_url + version + '/'!r}
html_theme_options["switcher"] = {{
    "json_url": {base_url + 'versions.json'!r},
    "version_match": {version!r},
}}
html_theme_options["navbar_center"] = ["version-switcher"]
# Read the shared manifest at page load so archived versions warn when superseded.
html_theme_options["show_version_warning_banner"] = True
# The manifest is deployed with this build and may not exist on the live site yet.
html_theme_options["check_switcher"] = False
''')

    elif command == "assemble":
        artifacts, site = map(Path, sys.argv[2:4])
        entries = json.loads(Path("versions.json").read_text())
        latest = entries[0]["version"]

        # Fail before assembling if any release build is missing or incomplete.
        for entry in entries:
            source = artifacts / f"docs-html-{entry['version']}"
            if not (source / "index.html").is_file():
                raise SystemExit(f"Missing documentation: {source}")
        site.mkdir(parents=True, exist_ok=False)
        for entry in entries:
            shutil.copytree(artifacts / f"docs-html-{entry['version']}", site / entry["version"])
            # The theme hardcodes "stable" in its banner button. Apply our label
            # during assembly so reused archives also say "latest" without rebuilding.
            for script in (site / entry["version"] / "_static").rglob("pydata-sphinx-theme.js"):
                script.write_text(script.read_text().replace("Switch to stable version", "Switch to latest version"))

        # Keep root assets and objects.inv working for existing consumers. Root
        # HTML redirects to versioned pages; older removed pages retain a target.
        shutil.copytree(site / latest, site, dirs_exist_ok=True)
        redirects = {}
        for entry in reversed(entries):
            version = entry["version"]
            for page in (site / version).rglob("*.html"):
                relative = page.relative_to(site / version)
                redirects[relative] = base_url + version + "/" + relative.as_posix()
        for relative, url in redirects.items():
            destination = site / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                f'<title>Documentation moved</title><link rel="canonical" href="{html.escape(url, quote=True)}">'
                f'<meta http-equiv="refresh" content="0; url={html.escape(url, quote=True)}">'
                f'<script>location.replace({json.dumps(url)} + location.search + location.hash);</script>'
                f'<a href="{html.escape(url, quote=True)}">Continue to documentation</a></html>\n'
            )

        # All releases fetch this shared manifest, so their menus stay current.
        switcher = [{
            "name": entry["version"] + (" (latest)" if entry["version"] == latest else ""),
            "version": entry["version"],
            "url": base_url + entry["version"] + "/",
            "preferred": entry["version"] == latest,
        } for entry in entries]
        (site / "versions.json").write_text(json.dumps(switcher, indent=2) + "\n")
        (site / ".nojekyll").touch()
    else:
        raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
