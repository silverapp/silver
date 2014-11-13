develop: setup-git
	pip install "file://`pwd`#egg=silver[dev]"
	pip install -e .
	pip install -r requirements/test.txt

setup-git:
	git config branch.autosetuprebase always
	cd .git/hooks && ln -sf ../../hooks/* ./

lint-python:
	@echo "Linting Python files"
	PYFLAKES_NODOCTEST=1 flake8 silver
	@echo ""

test:
	@DJANGO_SETTINGS_MODULE=silver.tests.test_settings py.test

.PHONY: develop setup-git lint-python test
