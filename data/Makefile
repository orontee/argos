.PHONY: check check-desktop-file check-gschemas clean distclean

gschemas.compiled: app.argos.Argos.gschema.xml
	glib-compile-schemas .

check: check-desktop-file check-gschemas

check-desktop-file: app.argos.Argos.desktop
	desktop-file-validate $<

check-gschemas: app.argos.Argos.gschema.xml
	glib-compile-schemas --dry-run .

clean:
	rm -f gschemas.compiled

distclean: clean
