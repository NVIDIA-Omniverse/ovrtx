# Makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Project root (absolute so paths work after cd)
PROJECT_ROOT  = $(abspath ..)

# Sphinx source and build dirs as absolute paths
DOCS_DIR      = $(PROJECT_ROOT)/docs

# The docs toolchain is declared standalone rather than as a pyproject.toml extra: it
# needs Sphinx >= 8.2, which needs Python >= 3.11, while ovrtx itself supports 3.10.
# See requirements.txt.
UV            ?= uv
UVRUN         = $(UV) run --no-project --python '>=3.11' --with-requirements $(DOCS_DIR)/requirements.txt

# Put it first so that "make" without argument is like "make help".
help:
	@$(UVRUN) $(SPHINXBUILD) -M help "$(DOCS_DIR)" "$(DOCS_DIR)/$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile doxygen clean html

# Run Doxygen to generate XML for Breathe
doxygen:
	@echo "Running Doxygen..."
	@mkdir -p _doxygen
	@doxygen Doxyfile

# Clean build artifacts
clean:
	@rm -rf $(BUILDDIR)
	@rm -rf _doxygen

# Build HTML with Doxygen first, using uv for dependencies
html: doxygen
	$(UVRUN) $(SPHINXBUILD) -M html "$(DOCS_DIR)" "$(DOCS_DIR)/$(BUILDDIR)" $(SPHINXOPTS) $(O)
