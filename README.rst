=====
argos
=====

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: http://www.mypy-lang.org/static/mypy_badge.svg
   :target: http://mypy-lang.org/

Gtk front-end to control a Mopidy server through a tiny touch screen.

.. figure:: screenshot.png
   :alt: Screenshot
   :align: center
   :width: 407
   :height: 249

   The application window

Features 🥳
~~~~~~~~~~~

* Play random album

* Configure and play favorite playlist

* Display album cover from Mopidy-Local HTTP API

Install
~~~~~~~

Install dependencies at system level::

  sudo apt install -y python3-gi python3-gi-cairo python3-aiohttp

Build and install::

  make
  make install

Run through your desktop application menu or the line command::

  python3 -m argos

For a list of supported command line arguments and defaults::

  python3 -m argos --help

Contributing
~~~~~~~~~~~~

One can install dependencies and configure pre-commit hooks in a
dedicated virtual environment using ``poetry``::

  sudo apt install libglib2.0-bin libglib2.0-dev-bin
  poetry shell
  poetry install
  pre-commit install

Pre-commit hooks run ``mypy`` check and make sure code is properly
formatted (using ``black``).

Run with ``--debug`` command-line option to output detailed logs::

  python3 -m argos --debug
