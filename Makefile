
PYTHON ?= python

dist:
	$(PYTHON) ./setup.py sdist

clean:
	rm -rf dist/

check:
	BZR_PLUGINS_AT=loggerhead@$$(pwd) bzr selftest -s bp.loggerhead
