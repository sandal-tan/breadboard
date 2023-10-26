install: deploy devices
	ampy put main.py

test: deploy
	#ampy run ./tests/test_led.py
	#ampy run ./tests/test_fan.py
	#ampy run ./tests/test_network.py
	ampy run ./tests/test_environment.py

repl: deploy
	rshell repl

devices:
	ampy put ./devices_${DEVICE}.json devices.json

deploy:
	ampy put ./breadboard
	ampy put favicon.ico
