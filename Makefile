full-test: test

test:
	DJANGO_SETTINGS_MODULE=settings_test pytest -vv

run:
	echo "TBA"

dependencies:
	pip install -U -r requirements/test.txt

build:
	echo "No need to build something. You may try 'make dependencies'."

lint:
	pep8 --max-line-length=100 --exclude=migrations,urls.py .

.PHONY: test full-test build lint run
