develop: setup-git
	pip install "file://`pwd`#egg=silver[dev]"
	pip install -e .
	pip install -r test_requirements.txt

setup-git:
	git config branch.autosetuprebase always
	cd .git/hooks && ln -sf ../../hooks/* ./

lint-python:
	@echo "Linting Python files"
	PYFLAKES_NODOCTEST=1 flake8 silver
	@echo ""
