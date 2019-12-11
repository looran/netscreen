PREFIX=/usr/local
BINDIR=$(PREFIX)/bin

all:
	@echo "Use \"sudo make install-client\" or \"sudo make install-server\""

install: install-client install-server

install-client:
	install -m 0755 netscreen.py $(BINDIR)/netscreen

install-server:
	install -m 0755 netscreend.py $(BINDIR)/netscreend
