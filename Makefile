.PHONY: test coverage

test:
	python3 -m doctest notion.py

coverage:
	coverage run -m doctest notion.py
	coverage report -m
