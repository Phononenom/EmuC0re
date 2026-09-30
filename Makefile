CC      = gcc
OBJCOPY = objcopy
PYTHON  = python3

CFLAGS  = -Os -ffreestanding -fno-stack-protector -fno-builtin \
          -fpie -mno-red-zone -fomit-frame-pointer -fcf-protection=none \
          -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables \
          -Wall -Wno-unused-function -Isrc

LDFLAGS = -T linker.ld -nostdlib -nostartfiles -static-pie \
          -Wl,--build-id=none -Wl,-z,norelro

SRCS    = src/main.c src/bus.c src/cpu.c src/ppu.c src/apu.c src/ftp.c
OBJS    = $(SRCS:.c=.o)
TARGET  = nes_emu

all: $(TARGET).bin

%.o: %.c src/core.h src/nes.h src/tables.h src/ftp.h
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET).elf: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(OBJS)

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@
	@echo "Built: $@ ($$(wc -c < $@) bytes)"

clean:
	rm -f src/*.o $(TARGET).elf $(TARGET).bin
	rm -rf dist

# Homebrew Browser packaging: dist/EmuC0re holds payload.bin (the blob
# verbatim) plus the manifest the browser reads to plan its JIT mappings.
# reserve is the SAME reservation mklua.py substitutes for @@JIT_SIZE@@,
# rounded up to whole 256KB chunks -- the granularity the browser remaps at.
# mkmanifest.py fails the build if the blob outgrows the reservation or the
# reservation outgrows the browser's 768KB JIT region.
dist: $(TARGET).bin $(TARGET).elf
	$(PYTHON) tools/mkmanifest.py EmuC0re $(TARGET).bin $(TARGET).elf dist/EmuC0re/manifest
	cp $(TARGET).bin dist/EmuC0re/payload.bin
	@cat dist/EmuC0re/manifest

.PHONY: all clean dist
