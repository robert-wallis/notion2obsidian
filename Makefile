.PHONY: test coverage

test:
	pytest --doctest-modules

coverage:
	coverage run --data-file .coverage-doctest -m pytest --doctest-modules notion2obsidian.py
	coverage run --data-file .coverage-100 notion2obsidian.py
	coverage combine .coverage-doctest .coverage-100
	coverage report -m notion2obsidian.py
