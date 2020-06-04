
PYTHON ?= python3

dist:
	$(PYTHON) ./setup.py sdist

clean:
	rm -rf dist/

check:
	BRZ_PLUGINS_AT=loggerhead@$$(pwd) brz selftest -s bp.loggerhead
