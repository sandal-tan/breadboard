test: deploy
	#ampy run ./tests/test_led_strip.py
	#ampy run ./tests/test_fan.py
	ampy run ./tests/test_network.py

repl: deploy
	rshell repl

deploy:
	ampy put ./pico_enclosure
	ampy put ./devices.json devices.json
