import logging

from discord.ext import commands

from bot.configs import Bot

logger = logging.getLogger("ItkBot")

__all__ = [
    "ItkBot",
]


class ItkBot(commands.Bot):
    def __init__(self, *args, **options) -> None:
        super().__init__(*args, **options)
        self.ext_path_mapping = {}
        self.ignore_kw_list = []

    def load_all_extensions(self) -> None:
        from bot.core import EXTENSIONS

        extensions = set(EXTENSIONS)
        for ext in extensions:
            self.load_extension(ext)

    def load_extension(self, name: str) -> None:
        super().load_extension(name)

        self.ext_path_mapping[name.rsplit(".", 1)[-1]] = name
        logger.info(f"Loaded | {name.rsplit('.', 1)[-1].capitalize()}")

    def unload_extension(self, name: str) -> None:
        super().unload_extension(name)

        del self.ext_path_mapping[name.rsplit(".", 1)[-1]]
        logger.info(f"Unloaded | {name.rsplit('.', 1)[-1].capitalize()}")

    def reload_extension(self, name: str) -> None:
        super().reload_extension(name)

        logger.info(f"Reloaded | {name.rsplit('.', 1)[-1].capitalize()}")

    async def on_ready(self) -> None:
        from random import choice

        from bot.configs import Emojis

        self.owner = self.get_user(Bot.owner)

        self.ignore_kw_list = []
        for cmd in self.commands:
            self.ignore_kw_list.append(cmd.name)
            for alias in cmd.aliases:
                self.ignore_kw_list.append(alias)
        for word in Bot.ignore_keywords:
            self.ignore_kw_list.append(word)

        logger.info("Bot is ready.")
        await self.get_channel(Bot.log_channel).send(
            f"親愛的海倫向你早安 {choice(Emojis.helens)}"
        )

    async def on_command(self, ctx: commands.Context) -> None:
        logger.trace(f"{ctx.author} ({ctx.author.id}) | `{ctx.message.content}`")
