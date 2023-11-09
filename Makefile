CONFIG_FILE ?= devices.json
BUILD_FILES = $(shell ls -d ./breadboard/**.py)

test: deploy
	#ampy run ./tests/test_led.py
	#ampy run ./tests/test_fan.py
	#ampy run ./tests/test_network.py
	ampy run ./tests/test_environment.py


install: build deploy configure clean run

debug:
	@poetry run mpremote run main.py

run:
	@poetry run mpremote run --no-follow main.py

configure:
	@poetry run mpremote cp $(CONFIG_FILE) :devices.json

deploy: build 
	@poetry run mpremote cp -r ./breadboard/**.mpy :
	@poetry run mpremote cp main.mpy :

build:
	@poetry run mpy-cross main.py
	@for file in $(BUILD_FILES) ; do \
		poetry run mpy-cross $$file ; \
	done

clean:
	@rm -rf main.mpy
	@rm -rf breadboard/**.mpy
