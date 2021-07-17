import random
from typing import Optional, Union

import discord
from bot import ItkBot
from bot.configs import Reactions
from bot.core import CogInit
from discord.ext import commands


class Cue(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        from bot.core import Mongo

        self.mongo = Mongo("discord_669934356172636199", "cue_list")

        self.cue_msg_details = []

    def _get_member_cue_list(self, member: discord.Member) -> list[str]:
        result = self.mongo.find({"_id": member.id})
        return result["list"] if result is not None else []

    def _get_updated_cue_embed(self) -> discord.Embed:
        current_page = self.cue_msg_details[1]
        total_page = self.cue_msg_details[2]
        member_cue_list = self.cue_msg_details[3]
        member = self.cue_msg_details[4]

        embed = discord.Embed()
        # Author
        embed.set_author(name=f"{member.display_name} 錯字大全")
        # Footer
        embed.set_footer(text=f"頁 {current_page + 1} / {total_page + 1}")
        # Thumbnail
        embed.set_thumbnail(url=member.avatar_url)
        # Fields
        start = current_page * 21
        end = start + 21
        for i, cue_string in enumerate(member_cue_list[start:end], start + 1):
            embed.add_field(name=i, value=cue_string, inline=True)

        return embed

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        if not self.cue_msg_details or self.cue_msg_details[0] is None:
            return

        if msg == self.cue_msg_details[0]:
            self.cue_msg_details = []

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User
    ) -> None:
        # 忽略來自機器人的 Emoji 添加事件
        if user.bot:
            return
        # 如果之前沒有列出語錄，或事件訊息不是語錄訊息，忽略
        if not self.cue_msg_details or reaction.message != self.cue_msg_details[0]:
            return
        await reaction.remove(user)

        details = self.cue_msg_details

        # 上一頁
        if str(reaction.emoji) == Reactions.prev_page:
            # 避免頁數出現負值
            if details[1] != 0:
                details[1] -= 1
        # 下一頁
        elif str(reaction.emoji) == Reactions.next_page:
            # 避免頁數超出總頁數
            if details[1] != details[2]:
                details[1] += 1
        # 首頁
        elif str(reaction.emoji) == Reactions.first_page:
            details[1] = 0
        # 末頁
        elif str(reaction.emoji) == Reactions.last_page:
            details[1] = details[2]

        embed = self._get_updated_cue_embed()
        await reaction.message.edit(embed=embed)

    @commands.group(name="cue", aliases=["c"], invoke_without_command=True)
    async def cue(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        pos: Optional[int] = None,
    ) -> None:
        # 有指定成員
        if member is not None:
            member_cue_list = self._get_member_cue_list(member)

            member_name = member.display_name
            # 有抓到語錄，發送語錄
            if member_cue_list:
                # 沒有指定位置則隨機指定
                if pos is None:
                    pos = random.randint(1, len(member_cue_list))
                cue_string = member_cue_list[pos - 1]

                await ctx.send(f"{member_name} 語錄 {pos} - {cue_string}")
            else:
                await ctx.send(f"{member_name} 沒有語錄")
            await ctx.message.delete()

        # 獲取所有已記錄的語錄
        cue_list = {doc["_id"]: doc["list"] for doc in self.mongo.find()}
        # 隨機選定 ID、語錄串列
        random_id, random_cue_list = random.choice(list(cue_list.items()))
        # 獲取成員名稱、位置、語錄
        member_name = self.bot.get_user(random_id).display_name
        pos = random.randint(1, len(random_cue_list))
        cue_string = random_cue_list[pos - 1]

        await ctx.send(
            f"{member_name} 語錄 {pos} - {cue_string}",
        )
        await ctx.message.delete()
        return

    @cue.command(aliases=["a"])
    async def add(self, ctx, member: discord.Member, *, cue_string) -> None:
        # 獲取已添加過的語錄
        member_cue_list = self._get_member_cue_list(member)

        # 未在清單內: 未添加過，更新
        if cue_string not in member_cue_list:
            self.mongo.update({"_id": member.id}, {"$push": {"list": cue_string}})

            member_name = member.display_name
            total_length = len(member_cue_list) + 1

            await ctx.reply(
                f"已新增 {member_name} 語錄 {total_length} - {cue_string}", delete_after=7
            )
            await ctx.message.delete(delay=7)
            return

        # 已在清單內: 已添加過，傳送提示
        await ctx.reply(f"{cue_string} 已經新增過了", delete_after=7)
        await ctx.message.delete(delay=7)
        return

    @cue.command(aliases=["remove", "d", "r"])
    async def delete(
        self, ctx, member: discord.Member, pos_or_string: Union[int, str]
    ) -> None:
        # 獲取已添加的語錄
        member_cue_list = self._get_member_cue_list(member)

        member_name = member.display_name
        # 沒有語錄無法刪除，傳送提示
        if not member_cue_list:
            await ctx.reply(f"{member_name} 沒有語錄喔", delete_after=7)
            await ctx.message.delete(delay=7)
            return

        pos = 0
        try:
            # 若輸入為 int，直接指派
            if isinstance(pos_or_string, int):
                pos = pos_or_string
            # 若輸入為 str，尋找並指派
            elif isinstance(pos_or_string, str):
                pos = member_cue_list.index(pos_or_string) + 1
        # 輸入字串不在語錄內
        except ValueError:
            await ctx.reply(f"輸入的值 {pos_or_string} 無效", delete_after=7)
            await ctx.message.delete(delay=7)
            return

        # 指定位置小於等於 0: 位置無效，傳送提示
        if pos <= 0:
            await ctx.reply("指定位置必須大於 1", delete_after=7)
            await ctx.message.delete(delay=7)
            return
        # 指定位置大於語錄長度: 位置無效，傳送提示
        elif pos > len(member_cue_list):
            await ctx.reply(f"{member_name} 沒有那麼多語錄可以刪啦", delete_after=7)
            await ctx.message.delete(delay=7)
            return

        # * 放於後方，避免輸入位置無效
        cue_string = member_cue_list[pos - 1]

        # 語錄刪除後少於等於零個，連同成員紀錄刪除
        if len(member_cue_list) <= 1:
            # 刪除成員紀錄
            self.mongo.delete({"_id": member.id})

            await ctx.reply(
                f"已刪除 {member_name} 語錄 {pos} - {cue_string}", delete_after=7
            )
            await ctx.message.delete(delay=7)
            return

        # 以 $pull 操作符刪除指定語錄
        self.mongo.update({"_id": member.id}, {"$pull": {"list": cue_string}})
        await ctx.reply(f"已刪除 {member_name} 語錄 {pos} - {cue_string}", delete_after=7)
        await ctx.message.delete(delay=7)

    @cue.command(aliases=["l"])
    async def list(self, ctx, member: discord.Member) -> None:
        await ctx.message.delete(delay=3)
        # 嘗試刪除之前已送出的排行訊息
        try:
            if self.cue_msg_details and self.cue_msg_details[0] is not None:
                await self.cue_msg_details[0].delete()
        except discord.NotFound:
            print("[Cue list] 找不到要刪除的訊息，已略過")
        member_name = member.display_name
        member_cue_list = self._get_member_cue_list(member)
        # 無語錄紀錄，傳送提示
        if not member_cue_list:
            await ctx.reply(f"{member_name} 沒有語錄喔", delete_after=7)
            await ctx.message.delete(delay=7)
            return

        total_page = len(member_cue_list) // 21
        # 初始化語錄訊息詳情
        self.cue_msg_details = [None, total_page, total_page, member_cue_list, member]

        # 取得要傳送的 Embed
        embed = self._get_updated_cue_embed()
        # 傳送 Embed 並記錄至詳情
        cue_list_message = await ctx.send(embed=embed)
        self.cue_msg_details[0] = cue_list_message

        # 添加反應
        await cue_list_message.add_reaction("<:first_page:806497548343705610>")
        await cue_list_message.add_reaction("<:prev_page:805002492848767017>")
        await cue_list_message.add_reaction("<:next_page:805002492525805589>")
        await cue_list_message.add_reaction("<:last_page:806497548558532649>")

    @commands.command(aliases=["ca"])
    async def cue_add(self, ctx, member: discord.Member, *, cue_string) -> None:
        # 使舊指令可執行
        await ctx.invoke(
            self.bot.get_command("cue add"), member=member, cue_string=cue_string
        )

    @commands.command(aliases=["cd", "cr"])
    async def cue_delete(
        self,
        ctx: commands.Context,
        member: discord.Member,
        pos_or_string: Union[int, str],
    ) -> None:
        # 使舊指令可執行
        await ctx.invoke(
            self.bot.get_command("cue delete"),
            member=member,
            pos_or_string=pos_or_string,
        )

    @commands.command(aliases=["cl"])
    async def cue_list(self, ctx: commands.Context, member: discord.Member) -> None:
        # 使舊指令可執行
        await ctx.invoke(self.bot.get_command("cue list"), member=member)


def setup(bot: ItkBot) -> None:
    bot.add_cog(Cue(bot))
