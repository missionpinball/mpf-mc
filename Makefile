integration:
	python3 -m unittest discover -s mpfmc/integration

unit:
	python3 -m unittest discover -s mpfmc/tests

unit-verbose:
	python3 -m unittest discover -v -s mpfmc/tests 2>&1

coverage:
	coverage3 run -m unittest discover -s mpfmc/tests
	coverage3 html
