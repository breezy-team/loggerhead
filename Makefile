
PYTHON ?= python3
BRZ ?= brz

dist:
	$(PYTHON) ./setup.py sdist

clean:
	rm -rf dist/

check:
	BRZ_PLUGINS_AT=loggerhead@$$(pwd) $(BRZ) selftest -s bp.loggerhead
