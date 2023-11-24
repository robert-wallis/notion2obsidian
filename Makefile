.PHONY: test coverage

test:
	pytest --doctest-modules

coverage:
	coverage run -m pytest --doctest-modules notion2obsidian.py
	coverage report -m notion2obsidian.py
