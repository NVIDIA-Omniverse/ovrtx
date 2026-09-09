# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Sphinx extension: filtered-literalinclude directive.

Extends ``literalinclude`` with two filtering options:

``:exclude-pattern:``
    Strips lines matching a regular expression.  The primary use-case is
    removing ``# [snippet:<name>]`` / ``// [snippet:<name>]`` markers that are
    present in example files for skill references but should not appear in
    rendered documentation.

``:omit-markers:``
    Strips entire regions delimited by ``# [omit]`` / ``# [/omit]`` (Python)
    or ``// [omit]`` / ``// [/omit]`` (C/C++) marker pairs.  Both the marker
    lines and all lines between them are removed.  Use this to hide
    test-only code (asserts, debug helpers) that lives inside a snippet but
    should not appear in rendered docs.
"""

import re

from docutils import nodes as docutils_nodes
from sphinx.directives.code import LiteralInclude


class FilteredLiteralInclude(LiteralInclude):
    """A ``literalinclude`` variant that can exclude lines by regex."""

    option_spec = {
        **LiteralInclude.option_spec,
        "exclude-pattern": str,
        "omit-markers": lambda x: True,  # flag option, no value
    }

    # Matches # [omit] / # [/omit] and // [omit] / // [/omit]
    _OMIT_OPEN = re.compile(r"^\s*(?:#|//)\s*\[omit\]\s*$")
    _OMIT_CLOSE = re.compile(r"^\s*(?:#|//)\s*\[/omit\]\s*$")

    def _apply_filters(self, text: str) -> str:
        lines = text.splitlines()

        # Strip omit regions first (order doesn't matter, but do it first
        # so exclude-pattern doesn't need to match inside omitted blocks).
        if "omit-markers" in self.options:
            kept = []
            omitting = False
            for line in lines:
                if self._OMIT_OPEN.search(line):
                    omitting = True
                    continue
                if self._OMIT_CLOSE.search(line):
                    omitting = False
                    continue
                if not omitting:
                    kept.append(line)
            lines = kept

        # Then strip individual lines matching exclude-pattern.
        pattern = self.options.get("exclude-pattern")
        if pattern:
            regex = re.compile(pattern)
            lines = [line for line in lines if not regex.search(line)]

        return "\n".join(lines)

    def run(self):
        nodes = super().run()

        has_filters = self.options.get("exclude-pattern") or "omit-markers" in self.options
        if not has_filters:
            return nodes

        # With :caption:, Sphinx wraps the literal_block in a container whose first
        # child is the caption. Filter the literal_block wherever it sits, so a
        # captioned include is not left with its caption replaced by code text.
        for node in nodes:
            for block in node.findall(docutils_nodes.literal_block):
                filtered = self._apply_filters(block.astext())
                # Update both rawsource (used by Pygments for highlighting)
                # and the child Text node (used for plain-text output)
                block.rawsource = filtered
                block.children[0] = block.children[0].__class__(filtered)

        return nodes


def setup(app):
    app.add_directive("filtered-literalinclude", FilteredLiteralInclude)
    return {"version": "0.1", "parallel_read_safe": True, "parallel_write_safe": True}
