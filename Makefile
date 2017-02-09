full-test: test

test:
	python manage.py test -v2

run:
	echo "TBA"

build:
	echo "No need to build someting"

lint:
	pep8 --max-line-length=100 --exclude=migrations,urls.py .

.PHONY: test full-test build lint run
