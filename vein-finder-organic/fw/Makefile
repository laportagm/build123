# Vein finder (organic) firmware - ATtiny1614.  Personal prototype, NOT a medical device.
#   make            build fw.hex (avr-gcc 14 from build/tools, see README)
#   make test       host unit tests of the device logic
#   make mutants    check that the tests catch 16 planted bugs in the safety logic
#   make flash      program over UPDI (Adafruit UPDI Friend / any serial adapter, pymcuprog)
#   make wdt-test   watchdog bench-test build (hangs 5 s after the LEDs come on; never for
#                   use): make flash HEX=build/fw_wdt_test.hex, then re-flash build/fw.hex
AVR    ?= ../build/tools/avr-gcc-14.1.0-x64-linux/bin
MCU     = attiny1614
CFLAGS  = -mmcu=$(MCU) -Os -std=gnu11 -Wall -Wextra -Werror -ffunction-sections -fdata-sections -DF_CPU=3333333UL
LDFLAGS = -mmcu=$(MCU) -Wl,--gc-sections
SRC     = src/main.c src/logic.c
PORT   ?= /dev/ttyUSB0
HEX    ?= build/fw.hex

all: build/fw.hex size check

build/fw.elf: $(SRC) src/logic.h
	mkdir -p build
	$(AVR)/avr-gcc $(CFLAGS) $(SRC) $(LDFLAGS) -o $@

build/fw.hex: build/fw.elf
	$(AVR)/avr-objcopy -O ihex -R .eeprom $< $@

size: build/fw.elf
	$(AVR)/avr-size $<

# static checks of the compiled code: race-free power-down entry, watchdog set and fed
check: build/fw.elf tools/check_build.py
	python3 tools/check_build.py $(AVR)/avr-objdump build/fw.elf

build/fw_wdt_test.hex: $(SRC) src/logic.h
	mkdir -p build
	$(AVR)/avr-gcc $(CFLAGS) -DVF_WDT_TEST $(SRC) $(LDFLAGS) -o build/fw_wdt_test.elf
	$(AVR)/avr-objcopy -O ihex -R .eeprom build/fw_wdt_test.elf $@

wdt-test: build/fw_wdt_test.hex

test: build/test_logic
	./build/test_logic

mutants: test/mutants.py test/test_logic.c src/logic.c src/logic.h
	python3 test/mutants.py

build/test_logic: test/test_logic.c src/logic.c src/logic.h
	mkdir -p build
	gcc -std=c11 -Wall -Wextra -Werror -O1 test/test_logic.c src/logic.c -lm -o $@

flash: $(HEX)
	pymcuprog write -t uart -u $(PORT) -d $(MCU) -f $(HEX) --erase --verify

clean:
	rm -rf build

.PHONY: all size check wdt-test test mutants flash clean
