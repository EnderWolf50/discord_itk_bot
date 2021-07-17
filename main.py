from discord import Intents

from bot import ItkBot
from bot.configs import Bot
from bot.log import logging_setup, sentry_setup

logging_setup()
sentry_setup()


itk_bot = ItkBot(
    command_prefix=Bot.prefix,
    description=Bot.description,
    case_insensitive=True,
    strip_after_prefix=True,
    help_command=None,
    intents=Intents.all(),
    owner_id=Bot.owner,
)
itk_bot.load_all_extensions()  # 讀取全部 extension

if __name__ == "__main__":
    itk_bot.run(Bot.token)
