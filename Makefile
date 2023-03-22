install: deploy
	ampy put main.py

test: deploy
	#ampy run ./tests/test_led.py
	#ampy run ./tests/test_fan.py
	#ampy run ./tests/test_network.py
	ampy run ./tests/test_environment.py

repl: deploy
	rshell repl

deploy:
	ampy put ./pico_enclosure
	ampy put ./devices.json devices.json
	ampy put favicon.ico
