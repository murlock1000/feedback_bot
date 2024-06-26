#!/usr/bin/env python3
import asyncio
import sys

# noinspection PyPackageRequirements

from feedback_bot.config import Config

try:
    from feedback_bot import main

    # Read config file

    # A different config file path can be specified as the first command line argument
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config.yaml"
    config = Config(config_path)

    # Run the main function of the bot
    asyncio.get_event_loop().run_until_complete(main.main(config))
except ImportError as e:
    print("Unable to import feedback_bot.main:", e)
