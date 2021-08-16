# Minimal makefile for Sphinx documentation
export CONFIG_DIR=service/config
export PYTHONPATH=service

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
	flask run --host=$(FLASK_HOST) --port=$(FLASK_PORT)

docs: Makefile
	$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean: Makefile
	$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
