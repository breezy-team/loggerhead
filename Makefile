
PYTHON ?= python

dist:
	$(PYTHON) ./setup.py sdist

clean:
	rm -rf dist/

check:
	# XXX MichaelHudson 2007-10-29 bug=158361: We can't run the loggerhead
	# tests in PQM yet :(
