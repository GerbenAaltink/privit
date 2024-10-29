
all: env build

env:
	-@rm -r ./venv
	python3 -m venv ./venv

run:
	./venv/bin/privit

utro:
	python privit/src/utro/cli.py http://127.0.0.1:8888/

build:
	
	. ./venv/bin/activate && cd privit && make build
