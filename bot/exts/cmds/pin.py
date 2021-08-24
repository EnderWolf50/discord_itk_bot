import random
from datetime import datetime as dt
from datetime import timedelta

import discord
from bot import ItkBot
from bot.configs import Emojis
from bot.core import CogInit
from bot.utils import MessageUtils
from discord.ext import commands


class Pin(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pins = {}
        self._channel_last_upd = {}

    async def _update_pins(self, channel_id: int) -> None:
        channel = self.bot.get_channel(channel_id)
        if not channel.permissions_for(channel.guild.me).is_superset(
            discord.Permissions(manage_messages=True)
        ):
            return
        self._pins[channel_id] = await channel.pins()
        self._channel_last_upd[channel_id] = dt.utcnow()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for channel in self.bot.get_all_channels():
            if not isinstance(channel, discord.TextChannel):
                continue
            await self._update_pins(channel.id)

    @commands.command()
    async def pin(self, ctx: commands.Context, user: discord.Member = None) -> None:
        if not ctx.guild:
            return

        channel_id = ctx.channel.id
        if (
            channel_id not in self._channel_last_upd
            or dt.utcnow() - self._channel_last_upd[channel_id] >= timedelta(minutes=5)
        ):
            await self._update_pins(channel_id)

        prepared_pin_list = (
            self._pins[channel_id]
            if user is None
            else [p for p in self._pins[channel_id] if p.author == user]
        )
        if len(prepared_pin_list) == 0:
            await MessageUtils.reply_then_delete(
                ctx, f"這個頻道沒有被釘選的訊息 {Emojis.pepe_nopes}"
            )
            return

        random_pin = random.choice(prepared_pin_list)
        random_pin_files = [
            await a.to_file(use_cached=True) for a in random_pin.attachments
        ]
        await ctx.send(
            f"{random_pin.author.display_name}：\n{random_pin.content}",
            files=random_pin_files,
        )


def setup(bot: ItkBot) -> None:
    bot.add_cog(Pin(bot))
