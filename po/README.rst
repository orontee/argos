============
Translations
============

Contributions welcome!

Howto
=====

People interested in contributing to translations should use the
corresponding `Weblate project
<https://hosted.weblate.org/projects/argos/argos/>`_.

Translations will be pushed by Weblate bot to Github source code
repository, on the ``translations`` branch.

This branch is manually merged in ``main`` branch periodically.

Technical considerations
========================

Translations are stored in `PO files </po>`_ which are textual,
editable files.

To update translation files to match current source code, one must
run::

  $ rm -rf builddir
  $ meson setup builddir .
  $ meson compile -C builddir io.github.orontee.Argos-update-po

💡 A oneliner is available::

  poetry run ./scripts/update-translations

Credits
=======

🙏🏼 Many, many thanks to all contributors!

The list of contributors to translations is extracted from the Weblate
project. It doesn't reflect the heavy contributions made by Heimen
Stoffels <vistausss@fastmail.com>, André Dokis
<em21nummer1@icloud.com> and JonyIvy <mail-github@luemkemann.de>
before the Weblate era.


* French

    * Matthias Meulien (orontee) <orontee@gmail.com> - 21


* Russian

    * gfbdrgng (gfbdrgng) <hnaofegnp@hldrive.com> - 200


* Spanish

    * Deleted User (deleted-48943) <noreply+48943@weblate.org> - 200
    * Matthias Meulien (orontee) <orontee@gmail.com> - 2


* Tamil

    * தமிழ்நேரம் (TamilNeram) <anishprabu.t@gmail.com> - 199
    * Matthias Meulien (orontee) <orontee@gmail.com> - 1
