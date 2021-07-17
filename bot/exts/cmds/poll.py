import discord
from bot import ItkBot
from bot.configs import Colors, Emojis, Reactions
from bot.core import CogInit
from discord.ext import commands


class Poll(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.poll_emojis = Reactions.numbers + Reactions.letters

    @commands.command(aliases=["vote"])
    async def poll(self, ctx: commands.Context, title: str, *options) -> None:
        len_of_options = len(options)

        # 反應數量上限為 20
        if 1 <= len_of_options <= 20:
            description = "".join(
                f"\n{self.poll_emojis[i]} {options[i]}" for i in range(len_of_options)
            )

            embed = discord.Embed(description=description, color=Colors.cyan)

            poll_msg = await ctx.send(title, embed=embed)
            for i in range(len_of_options):
                await poll_msg.add_reaction(self.poll_emojis[i])
        elif len_of_options < 1:
            await ctx.reply(f"你沒有輸入選項 {Emojis.pepe_pog_champ}", delete_after=7)
            await ctx.message.delete(delay=7)
        else:
            await ctx.reply(f"反應只能有 20 個 {Emojis.pepe_sad}", delete_after=7)
            await ctx.message.delete(delay=7)


def setup(bot: ItkBot) -> None:
    bot.add_cog(Poll(bot))
