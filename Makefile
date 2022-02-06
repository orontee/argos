VERSION=0.1.0

.PHONY: build check clean data distclean install uninstall

build: dist/argos-$(VERSION)-py3-none-any.whl

data:
	$(MAKE) -C $@

dist/argos-$(VERSION)-py3-none-any.whl: data
	poetry build

distclean: clean
	$(MAKE) -C data $@
	rm -rf dist

clean:
	$(MAKE) -C data $@

check:
	$(MAKE) -C data $@

install: dist/argos-$(VERSION)-py3-none-any.whl
	python3 -m pip install --no-deps --force-reinstall $<
	cp data/app.argos.Argos.desktop ~/.local/share/applications/
	mkdir -p ~/.local/share/argos/schemas
	cp data/gschemas.compiled data/app.argos.Argos.gschema.xml ~/.local/share/argos/schemas/

uninstall:
	python3 -m pip uninstall argos
	rm -f ~/.local/share/applications/app.argos.Argos.desktop
	rm -f ~/.local/share/argos/schemas/app.argos.Argos.gschema.xml ~/.local/share/argos/schemas/gschemas.compiled
