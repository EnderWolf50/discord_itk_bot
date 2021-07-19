import random

from bot import ItkBot
from bot.configs import Emojis
from bot.core import CogInit
from discord.ext import commands


class Choose(CogInit):
    @commands.command(aliases=["ch"])
    async def choose(self, ctx: commands.Context, *choices) -> None:
        await ctx.message.delete(delay=3)
        if len(choices) < 1:
            await ctx.reply(f"你沒有輸入選項 {Emojis.rainbow_pepe_angry}", delete_after=5)
            return
        await ctx.author.send(random.choice(choices))


def setup(bot: ItkBot) -> None:
    bot.add_cog(Choose(bot))
