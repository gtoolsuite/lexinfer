#
# Common logger, customizes loguru's logger
#

from loguru import logger

### General utilities
import argparse
import contextlib
import os
import sys


class Loginfer():


    #
    # Add DETAIL loglevel as more detailed INFO
    #
    logger.level("DETAIL", no=13, color="<cyan>")

    # Ensure class is abstract
    def __init__(self):
        logger.critical("Trying to create Loginfer object, aborting")
        quit()

    #
    # Set and process command line arguments
    #
    def set_cmdline_arguments(parser):
        ### TODO: add help info
        parser.add_argument("--loglevel", type=str, required=False, default="INFO")
        parser.add_argument("--logfile",  type=str, required=False)

    def process_cmdline_arguments(args):
        level = args["loglevel"]
        ### args must be result of vars(parser.parse_args())
        if args["logfile"] != None:
            sink = args["logfile"]
            with contextlib.suppress(FileNotFoundError):
                os.remove(sink)
        else:
            sink = sys.stderr
        logger.remove()
        logger.add(sink, level=level)

