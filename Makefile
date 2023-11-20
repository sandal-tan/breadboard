CONFIG_FILE ?= breadboard.json
BUILD_FILES = $(shell find breadboard -type f -name \*.py)

test: deploy
	#ampy run ./tests/test_led.py
	#ampy run ./tests/test_fan.py
	#ampy run ./tests/test_network.py
	ampy run ./tests/test_environment.py


install: build deploy configure clean

debug:
	@poetry run mpremote run main.py

run:
	@poetry run mpremote run --no-follow main.py

configure:
	@poetry run mpremote cp $(CONFIG_FILE) :breadboard.json

deploy: build 
	@cd build && poetry run mpremote cp -r breadboard : && cd -
	@poetry run mpremote cp main.py :

build:
	@mkdir -p build/breadboard/api
	@for file in $(BUILD_FILES) ; do \
		poetry run mpy-cross -o "build/$${file%.py}.mpy" $$file ; \
	done

clean:
	@rm -rf build/

echo:
	@for file in $(BUILD_FILES) ; do \
		echo $${file%.py}.mpy ; \
	done
