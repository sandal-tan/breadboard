install: deploy devices
	ampy put main.py

test: deploy
	#ampy run ./tests/test_led.py
	#ampy run ./tests/test_fan.py
	#ampy run ./tests/test_network.py
	ampy run ./tests/test_environment.py

run:
	rshell repl '~ import main'

devices:
	mpremote cp ${CONFIG_FILE} :devices.json

deploy:
	mpremote cp -r ./breadboard :
