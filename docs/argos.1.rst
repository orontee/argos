=====
argos
=====

----------------------------------------------------
Client for the Mopidy music server
----------------------------------------------------

:Manual section: 1

SYNOPSIS
========

**argos** [*OPTIONS*]

DESCRIPTION
===========

Argos is a graphical front-end for Mopidy. It connects to a local or
remote Mopidy server, whose URL is set in the preferences dialog or
with the ``mopidy-base-url`` GSettings key.

Custom styles must be gathered in the file
``~/.config/argos/style.css``. To adapt to devices with small touch
screen, one may have to tweak buttons appearance.

Many actions are exposed through D-Bus and thus available to script
the application.


OPTIONS
=======

--debug
    Enable debug output.

--hide-close-button
    Hide the close window button.

--hide-search-button
    Hide the search button.

--no-tooltips
    Do not display tooltips.

FILES
=====

*~/.config/argos/style.css*
    Custom GTK CSS styles.

EXAMPLES
========

Set the Mopidy server URL from the command line::

    gsettings set io.github.orontee.Argos mopidy-base-url \
                  http://192.168.1.45:6680

The following command illustrates how to use the DBUS interface to
enable dark theme::

    busctl --user call io.github.orontee.Argos \
                       /io/github/orontee/Argos \
                       org.gtk.Actions Activate \
                       "sava{sv}" "enable-dark-theme" 1 b true 0

SEE ALSO
========

**mopidy**\(1), **gsettings**\(1)
