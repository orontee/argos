#!/usr/bin/env python3

"""Mopidy UI for argos.

"""
import sys

from .app import Application


if __name__ == "__main__":
    app = Application()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
