
PYTHON ?= python

dist:
	$(PYTHON) ./setup.py sdist

clean:
	rm -rf dist/

