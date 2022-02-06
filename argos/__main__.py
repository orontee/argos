#!/usr/bin/env python3

import importlib.resources
import sys

from gi.repository import Gio


if __name__ == "__main__":
    with importlib.resources.path("argos", "app.argos.Argos.gresource") as path:
        resource = Gio.Resource.load(str(path))
    resource._register()

    from .app import Application
    app = Application()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
