.PHONY: check check-desktop-file check-gschemas clean compile-resources distclean

build: gschemas.compiled compile-resources

gschemas.compiled: app.argos.Argos.gschema.xml
	glib-compile-schemas .

compile-resources: app.argos.Argos.gresource.xml
	glib-compile-resources --target=../argos/app.argos.Argos.gresource $<

check: check-desktop-file check-gschemas

check-desktop-file: app.argos.Argos.desktop
	desktop-file-validate $<

check-gschemas: app.argos.Argos.gschema.xml
	glib-compile-schemas --dry-run .

clean:
	rm -f gschemas.compiled
	rm -f ../argos/app.argos.Argos.gresource

distclean: clean
