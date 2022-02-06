=====
argos
=====

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

Gtk front-end to control a Mopidy server through a tiny touch screen.

.. figure:: screenshot.png
   :alt: Screenshot
   :align: center
   
   The application window

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

One can install dependencies in a dedicated virtual environment using
``poetry``::

  poetry shell
  poetry install
  python3 -m argos --debug 

Run ``mypy``::

  poetry run mypy

Make sure code is properly formatted (using ``black``)::

  poetry run black

