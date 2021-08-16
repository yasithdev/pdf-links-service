# Minimal makefile for Sphinx documentation

export FLASK_ENV=development
export FLASK_APP=api.py
export FLASK_PORT=8000
export FLASK_HOST=0.0.0.0

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs/
BUILDDIR      = docs/_build

serve:
	cd pdflinks; flask run --host=$(FLASK_HOST) --port=$(FLASK_PORT)

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
