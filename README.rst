=====
argos
=====

Gtk front-end to control a Mopidy server through a tiny touch screen.

.. figure:: screenshot.png
   :alt: Screenshot
   :align: center
   
   The application window

Install
~~~~~~~

Install dependencies at system level::

  sudo apt install -y python3-gi python3-gi-cairo python3-aiohttp

Finally run::

  python3 -m argos

Debug
~~~~~

One must first stop the service if installed::

  python3 -m argos --debug 

For a list of supported command line arguments and defaults::

  python3 -m argos --help
