#!/usr/bin/env python3

"""Mopidy UI for argos.

"""

import argparse
import logging
import sys

from .app import Application

LOGGER = logging.getLogger("argosui")


def configure_logger(args: argparse.Namespace) -> None:
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    ch.setFormatter(formatter)
    level = logging.DEBUG if args.debug is True else logging.INFO
    ch.setLevel(level)
    logger = logging.getLogger("argosui")
    logger.setLevel(level)
    logger.addHandler(ch)


if __name__ == "__main__":
    app = Application()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
