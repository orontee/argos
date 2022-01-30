#!/usr/bin/env python3

"""Mopidy UI for argos.

"""

import argparse
import logging
import sys

from .app import Application

LOGGER = logging.getLogger("argosui")


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--debug", action="store_true",
                        help="enable debug logs")

    return parser


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
    parser = get_parser()
    args = parser.parse_args()

    configure_logger(args)

    app = Application()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
