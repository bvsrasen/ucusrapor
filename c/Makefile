CC ?= gcc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Wpedantic -Wconversion -Wdouble-promotion -Werror

build/tepe_cli: tepe_cli.c tepe.c tepe.h | build
	$(CC) $(CFLAGS) -o $@ tepe_cli.c tepe.c -lm

build:
	mkdir -p build

# Cortex-M4F (STM32F4) için kod boyutu; arm-none-eabi-gcc gerekiyor
arm: | build
	arm-none-eabi-gcc -std=c99 -Os -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 \
		-Wall -Wextra -Werror -c tepe.c -o build/tepe_m4.o
	arm-none-eabi-size build/tepe_m4.o

clean:
	rm -rf build

.PHONY: arm clean
