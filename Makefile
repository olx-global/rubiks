PYYAML_VERSION=3.12

all:

yaml: vendor/2/lib/yaml/__init__.py vendor/3/lib/yaml/__init__.py

vendor/2/lib/yaml/__init__.py: build/PyYAML-${PYYAML_VERSION}/setup.py
	rm -rf vendor/2/lib/yaml
	mkdir -p vendor/2/lib/yaml
	rsync -av build/PyYAML-${PYYAML_VERSION}/lib/yaml/. vendor/2/lib/yaml/.
	touch vendor/2/lib/yaml/__init__.py

vendor/3/lib/yaml/__init__.py: build/PyYAML-${PYYAML_VERSION}/setup.py
	rm -rf vendor/3/lib/yaml
	mkdir -p vendor/3/lib/yaml
	rsync -av build/PyYAML-${PYYAML_VERSION}/lib3/yaml/. vendor/3/lib/yaml/.
	touch vendor/3/lib/yaml/__init__.py

build/PyYAML-${PYYAML_VERSION}.tar.gz:
	mkdir -p build
	curl -o 'build/PyYAML-${PYYAML_VERSION}.tar.gz' 'http://pyyaml.org/download/pyyaml/PyYAML-${PYYAML_VERSION}.tar.gz'

build/PyYAML-${PYYAML_VERSION}/setup.py: build/PyYAML-${PYYAML_VERSION}.tar.gz
	rm -rf build/PyYAML-${PYYAML_VERSION}
	cd build && tar zxvf PyYAML-${PYYAML_VERSION}.tar.gz
	touch build/PyYAML-${PYYAML_VERSION}/setup.py

test: clean
	@PYTHON="$${PYTHON-python}"; export PYTHONPATH=test/test:lib; \
	echo "testing all (with $${PYTHON}) in test/test/test_*.py..."; \
	for i in test/test/test_*.py; do \
	  basename="$${i##*/}"; modules="$${modules} $${basename%.py}"; \
	done; \
	"$${PYTHON}" -m unittest $${modules}

coverage: clean checkdeps
	@PYTHON="$${PYTHON-python}"; export PYTHONPATH=test/test:lib; \
	echo "testing all (with $${PYTHON}) in test/test/test_*.py..."; \
	for i in test/test/test_*.py; do \
	  COVERAGE_FILE=.coverage_$${i##*/} "$${PYTHON}" -m coverage run $${i}; \
	done; \
	"$${PYTHON}" -m coverage combine .coverage_*; \
	"$${PYTHON}" -m coverage report

	${MAKE} clean

checkdeps:
	@PYTHON="$${PYTHON-python}"; export PYTHONPATH=test/test:lib; \
	if ! $${PYTHON} -c "import coverage" &> /dev/null; then \
		echo 'Unable to find coverage module on your python.'; \
		exit 1; \
	fi \

clean:
	@find . -type f -name '*.py[co]' -print0 | xargs -0 rm
	@find . -type d -name '__pycache__' -print0 | xargs -0 rm -r
	@find . -type f -name '.coverage' -print0 | xargs -0 rm 

.PHONY: yaml test clean
