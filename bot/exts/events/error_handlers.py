import logging

import discord
from bot import ItkBot
from bot.configs import Bot, Emojis
from bot.core import CogInit
from discord.ext import commands
from discord.ext.commands import errors
from sentry_sdk import push_scope

logger = logging.getLogger(__name__)


class ErrorHandlers(CogInit):
    @staticmethod
    def _error_embed_gen(ctx: commands.Context, e: errors) -> discord.Embed:
        embed = discord.Embed(
            title=f"{ctx.prefix}{ctx.command}",
            description=f"{ctx.author} | `{ctx.author.id}`",
        )
        # Thumbnail
        embed.set_thumbnail(url=ctx.author.avatar_url)
        # Fields
        embed.add_field(name=e.__class__.__name__, value=e, inline=True)
        return embed

    @commands.Cog.listener()
    async def on_error(self, event: str, *args, **kwargs):
        with push_scope() as scope:
            scope.set_tag("event", event)
            scope.set_extra("args", args)
            scope.set_extra("kwargs", kwargs)

            logger.exception(f"Unhandled exception in {event}.")

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, e: errors.CommandError
    ) -> None:
        if hasattr(e, "handled"):
            return  # 略過

        if isinstance(e, errors.CommandNotFound) and not getattr(
            ctx, "invoked_from_error_handler", False
        ):
            return  # 略過

        await ctx.message.delete(delay=13)
        await self.bot.get_channel(Bot.log_channel).send(
            content=f"{self.bot.owner.mention}", embed=self._error_embed_gen(ctx, e)
        )

        if isinstance(e, errors.CommandInvokeError):
            await self._command_invoke_error_handler(ctx, e)
        elif isinstance(e, errors.CheckFailure):
            await self._check_failure_handler(ctx, e)
        elif isinstance(e, errors.UserInputError):
            await self._user_input_error_handler(ctx, e)
        elif isinstance(e, errors.DisabledCommand):
            await ctx.reply(
                f"該指令被禁用或無法直接使用",
                delete_after=13,
            )
            return  # 不紀錄
        elif isinstance(e, errors.CommandOnCooldown):
            await ctx.reply(
                f"該指令還在冷卻｜{e.retry_after:.2f}s ", delete_after=e.retry_after
            )
            return  # 不紀錄
        else:
            await self._unexpected_error_handler(ctx, e)
            return  # 不做普通紀錄

        logger.debug(
            f"Command {ctx.command} invoked by {ctx.author} ({ctx.author.id}) | "
            f"{e.__class__.__name__}: {e}",
            exc_info=e,
        )

    async def _command_invoke_error_handler(
        self, ctx: commands.Context, e: errors.CommandInvokeError
    ):
        await ctx.reply(f"{self.bot.owner.mention} 該除蟲囉 {Emojis.pepe_coffee}")

    async def _user_input_error_handler(
        self, ctx: commands.Context, e: errors.UserInputError
    ) -> None:
        if isinstance(e, errors.BadArgument):
            await self._bad_argument_handler(ctx, e)
        elif isinstance(e, errors.MissingRequiredArgument):
            await ctx.reply(
                f"你好像少打了一些東西 {Emojis.pepe_hmm}",
                delete_after=13,
            )
        elif isinstance(e, errors.ArgumentParsingError):
            await ctx.reply(
                f"請重新確認輸入的引號位置 {Emojis.pepe_coin}",
                delete_after=13,
            )
        elif isinstance(e, errors.BadUnionArgument):
            await ctx.reply(
                f"參數轉換錯誤 {Emojis.bongo_pepe}",
                delete_after=13,
            )
        elif isinstance(e, errors.TooManyArguments):
            await ctx.reply(
                f"你輸入太多參數了 {Emojis.pepe_facepalm}",
                delete_after=13,
            )
        await ctx.invoke(self.bot.get_command(f"help {ctx.command}"))

    @staticmethod
    async def _bad_argument_handler(
        ctx: commands.Context, e: errors.BadUnionArgument
    ) -> None:
        if isinstance(e, errors.MessageNotFound):
            await ctx.reply(
                f"找不到訊息 {e.argument} {Emojis.pepe_sad}",
                delete_after=13,
            )
        elif isinstance(e, errors.ChannelNotFound):
            await ctx.reply(
                f"找不到頻道 {e.argument} {Emojis.pepe_sad}",
                delete_after=13,
            )
        elif isinstance(e, errors.RoleNotFound):
            await ctx.reply(
                f"找不到身分組 {e.argument} {Emojis.pepe_sad}",
                delete_after=13,
            )
        elif isinstance(e, (errors.UserNotFound, errors.MemberNotFound)):
            await ctx.reply(
                f"誰是 {e.argument} {Emojis.pepe_hmm}",
                delete_after=13,
            )
        elif isinstance(
            e, (errors.EmojiNotFound, errors.PartialEmojiConversionFailure)
        ):
            await ctx.reply(
                f"{e.argument} 是指哪個表符 {Emojis.pepe_hmm}",
                delete_after=13,
            )
        elif isinstance(e, errors.BadBoolArgument):
            await ctx.reply(
                f"我看不懂 {e.argument} 代表的布林值 {Emojis.pepe_nopes}",
                delete_after=13,
            )
        elif isinstance(e, (errors.BadColourArgument, errors.BadColorArgument)):
            await ctx.reply(
                f"我沒看過叫 {e.argument} 的顏色 {Emojis.rainbow_pepe_angry}",
                delete_after=13,
            )
        elif isinstance(e, errors.BadInviteArgument):
            await ctx.reply(
                f"你給的邀請連結好像沒用 {Emojis.pepe_sus}",
                delete_after=13,
            )
        elif isinstance(e, errors.ChannelNotReadable):
            await ctx.reply(
                f"我沒有權限讀取{e.argument.mention}...{Emojis.pepe_hands}",
                delete_after=13,
            )
        else:
            await ctx.reply(
                f"不知道你打錯了什麼，我想你該檢查後重試 {Emojis.pepe_hmm}",
                delete_after=13,
            )

    @staticmethod
    async def _check_failure_handler(
        ctx: commands.Context, e: errors.CheckFailure
    ) -> None:
        BOT_MISSING_ERRORS = (
            errors.BotMissingAnyRole,
            errors.BotMissingPermissions,
            errors.BotMissingRole,
        )

        USER_MISSING_ERRORS = (
            errors.MissingAnyRole,
            errors.MissingPermissions,
            errors.MissingRole,
        )
        if isinstance(e, USER_MISSING_ERRORS):
            await ctx.reply(
                f"**你**沒有足夠的權限執行指令 {Emojis.pepe_nopes}",
                delete_after=13,
            )
        elif isinstance(e, BOT_MISSING_ERRORS):
            await ctx.reply(
                f"**我**沒有足夠的權限執行指令 {Emojis.pepe_depressed}",
                delete_after=13,
            )

        if isinstance(e, errors.NotOwner):
            await ctx.reply(
                f"只有擁有者可以使用這個指令 {Emojis.pepe_crown_flip}",
                delete_after=13,
            )
        elif isinstance(e, errors.NSFWChannelRequired):
            await ctx.reply(
                f"請不要在這裡開車 {Emojis.pepe_monkaSTEER}",
                delete_after=13,
            )
        elif isinstance(e, errors.PrivateMessageOnly):
            await ctx.reply(
                f"這個指令**只能*在私人訊息中使用 {Emojis.rainbow_pepe_angry}",
                delete_after=13,
            )
        elif isinstance(e, errors.NoPrivateMessage):
            await ctx.reply(
                f"這個指令**無法**在私人訊息中使用 {Emojis.rainbow_pepe_angry}",
                delete_after=13,
            )
        elif isinstance(e, errors.CheckAnyFailure):
            await ctx.reply(
                f"未通過以下檢查 {Emojis.pepe_hmm}\n"
                f"`{'`, `'.join({e.__class__.__name__ for e in e.errors})}`",
                delete_after=13,
            )

    @staticmethod
    async def _unexpected_error_handler(
        ctx: commands.Context, e: errors.CommandError
    ) -> None:
        with push_scope() as scope:
            scope.user = {"id": ctx.author.id, "username": str(ctx.author)}

            scope.set_tag("command", ctx.command.qualified_name)
            scope.set_tag("message_id", ctx.message.id)
            scope.set_tag("channel_id", ctx.channel.id)

            scope.set_extra("message_content", ctx.message.content)

            if ctx.guild is not None:
                scope.set_extra(
                    "jump_to",
                    "https://discordapp.com/channels/"
                    f"{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}",
                )

            logger.error(
                "Error executing command invoked by "
                f"{ctx.message.author}: {ctx.message.content}",
                exc_info=e,
            )


def setup(bot: ItkBot) -> None:
    bot.add_cog(ErrorHandlers(bot))
