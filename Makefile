# xbmfont - embedded bitmap fonts for Xlib
#
#   make            build the example viewer (examples/xbfview)
#   make fonts BDF=/path/to/misc-fixed   regenerate fonts/ from BDF files
#   make clean
#
# The library itself is the single header xbmfont.h: nothing to build or link
# besides -lX11.

# Keep the previous behaviour: i386 toolchains link statically unless told otherwise.
TARGET_MACHINE := $(shell $(CC) -dumpmachine)
ifneq ($(findstring i386,$(TARGET_MACHINE)),)
    STATIC ?= 1
endif

CC      ?= gcc
CFLAGS  ?= -Os
CFLAGS  += -std=gnu99 -Wall -Wextra -Wshadow -ffunction-sections -fdata-sections -I.
LDFLAGS += -Wl,--gc-sections,--sort-common,-s
LDLIBS  += -lX11

ifeq ($(STATIC),1)
    LDFLAGS += -static
endif

FONTS = 5x8 6x10 6x13 7x14 9x15 9x18 10x20

all: examples/xbfview

examples/xbfview: examples/xbfview.c xbmfont.h $(wildcard fonts/*.h)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS) $(LDLIBS)

# Regenerate the font headers. BDF = directory with the misc-fixed BDF files
# (Markus Kuhn's ucs-fonts, see fonts/README.md). The converter refuses any
# file whose COPYRIGHT property does not say "Public domain".
fonts:
	@test -n "$(BDF)" || { echo "usage: make fonts BDF=/path/to/bdf-dir"; exit 1; }
	@for f in $(FONTS); do \
		python3 tools/bdf2xbf.py $(BDF)/$$f.bdf fixed_$$f fonts/xbf_fixed_$$f.h || exit 1; \
	done
	python3 tools/bdf2xbf.py $(BDF)/6x13B.bdf fixed_6x13b fonts/xbf_fixed_6x13b.h

clean:
	rm -f examples/xbfview

.PHONY: all fonts clean
