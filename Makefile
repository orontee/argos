VERSION=0.1.0

.PHONY: argos build check clean distclean install uninstall

build: dist/argos-$(VERSION)-py3-none-any.whl

argos:
	$(MAKE) -C $@

distclean: clean
	$(MAKE) -C argos $@
	rm -rf dist

clean:
	$(MAKE) -C argos $@

check:
	desktop-file-validate data/app.argos.Argos.desktop

install: dist/argos-$(VERSION)-py3-none-any.whl
	python3 -m pip install $<
	cp data/app.argos.Argos.desktop ~/.local/share/applications/

uninstall:
	python3 -m pip uninstall argos
	rm -f ~/.local/share/applications/data/app.argos.Argos.desktop

dist/argos-$(VERSION)-py3-none-any.whl: argos
	poetry build
