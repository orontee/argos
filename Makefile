VERSION=0.1.0

.PHONY: argos build check clean data distclean install uninstall

build: dist/argos-$(VERSION)-py3-none-any.whl data

argos:
	$(MAKE) -C $@

data:
	$(MAKE) -C $@

dist/argos-$(VERSION)-py3-none-any.whl: argos
	poetry build

distclean: clean
	$(MAKE) -C argos $@
	$(MAKE) -C data $@
	rm -rf dist

clean:
	$(MAKE) -C argos $@

check:
	$(MAKE) -C data $@

install: build
	python3 -m pip install $<
	cp data/app.argos.Argos.desktop ~/.local/share/applications/
	mkdir -p ~/.local/share/argos/schemas
	cp data/gschemas.compiled ~/.local/share/argos/schemas/

uninstall:
	python3 -m pip uninstall argos
	rm -f ~/.local/share/applications/app.argos.Argos.desktop
	rm -f ~/.local/share/argos/schemas/gschemas.compiled
