# Vein finder (organic) firmware - ATtiny1614.  Personal prototype, NOT a medical device.
#   make            build fw.hex (avr-gcc 14 from build/tools, see README)
#   make test       host unit tests of the device logic
#   make flash      program over UPDI (Adafruit UPDI Friend / any serial adapter, pymcuprog)
AVR    ?= ../build/tools/avr-gcc-14.1.0-x64-linux/bin
MCU     = attiny1614
CFLAGS  = -mmcu=$(MCU) -Os -std=gnu11 -Wall -Wextra -Werror -ffunction-sections -fdata-sections -DF_CPU=3333333UL
LDFLAGS = -mmcu=$(MCU) -Wl,--gc-sections
SRC     = src/main.c src/logic.c
PORT   ?= /dev/ttyUSB0

all: build/fw.hex size

build/fw.elf: $(SRC) src/logic.h
	mkdir -p build
	$(AVR)/avr-gcc $(CFLAGS) $(SRC) $(LDFLAGS) -o $@

build/fw.hex: build/fw.elf
	$(AVR)/avr-objcopy -O ihex -R .eeprom $< $@

size: build/fw.elf
	$(AVR)/avr-size $<

test: build/test_logic
	./build/test_logic

build/test_logic: test/test_logic.c src/logic.c src/logic.h
	mkdir -p build
	gcc -std=c11 -Wall -Wextra -Werror -O1 test/test_logic.c src/logic.c -lm -o $@

flash: build/fw.hex
	pymcuprog write -t uart -u $(PORT) -d $(MCU) -f build/fw.hex --erase --verify

clean:
	rm -rf build

.PHONY: all size test flash clean
