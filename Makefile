full-test: test

test:
	python manage.py test -v2

run:
	echo "TBA"

build:
	echo "No need to build someting"

lint:
	echo "TBA"

.PHONY: test full-test build lint run
