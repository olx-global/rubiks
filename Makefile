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

test:
	@PYTHON="$${PYTHON-python}"; export PYTHONPATH=test/test:lib; \
	echo "testing all (with $${PYTHON}) in test/test/test_*.py..."; \
	for i in test/test/test_*.py; do \
	  basename="$${i##*/}"; modules="$${modules} $${basename%.py}"; \
	done; \
	"$${PYTHON}" -m unittest $${modules}

.PHONY: yaml test
