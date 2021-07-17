from typing import Union

import discord
from bot import ItkBot
from bot.configs import Bot, Reactions
from bot.core import CogInit
from bot.utils import MessageUtils
from discord.ext import commands


class EmojiRank(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        from bot.core import Mongo

        self.mongo = Mongo("discord_669934356172636199", "emoji_rank")

        self.rank_msg_details = []

    def _db_add_emoji(self, emoji: Union[discord.abc.Snowflake, discord.Emoji]) -> None:
        # 若傳入的是 ID，先透過群組獲得 Emoji 物件
        if not isinstance(emoji, discord.Emoji):
            emoji = self.bot.get_emoji(emoji)

        self.mongo.update(
            {"_id": emoji.id},
            {
                "$set": {
                    "_id": emoji.id,
                    "name": emoji.name,
                    "animated": emoji.animated,
                    "count": 0,
                }
            },
        )

    def _db_delete_emoji(
        self, emoji: Union[discord.abc.Snowflake, discord.Emoji]
    ) -> None:
        # 若傳進來的是 Emoji 物件，將變數設為其 ID
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id

        self.mongo.delete({"_id": emoji})

    def _db_update_emoji(
        self, emoji: Union[discord.abc.Snowflake, discord.Emoji]
    ) -> None:
        # 若傳進來的是 ID，先透過群組獲得 Emoji 物件
        if not isinstance(emoji, discord.Emoji):
            emoji = self.bot.get_emoji(emoji)

        self.mongo.update(
            {"_id": emoji.id},
            {
                "$set": {
                    "name": emoji.name,
                }
            },
            upsert=False,
        )  # 不符合 query 不自動添加

    async def _guild_emoji_list(self) -> set[discord.abc.Snowflake]:
        guild = await self.bot.fetch_guild(Bot.main_guild)
        return {emo.id for emo in guild.emojis}

    async def _mongo_emoji_list(self) -> set[discord.abc.Snowflake]:
        return {emo["_id"] for emo in self.mongo.find()}

    async def _get_updated_rank_embed(self) -> discord.Embed:
        current_page = self.rank_msg_details[1]
        total_page = self.rank_msg_details[2]
        rank_data = self.rank_msg_details[3]

        embed = discord.Embed()
        # Author
        embed.set_author(
            name=f"表符使用率排名 {current_page * 12 + 1} ~ {current_page * 12 + 12}"
        )
        # Footer
        embed.set_footer(text=f"頁 {current_page + 1} / {total_page + 1}")
        # Thumbnail
        embed.set_thumbnail(url=(await self.bot.fetch_guild(Bot.main_guild)).icon_url)
        # Fields
        start = current_page * 12
        end = start + 12
        for rank, emoji in enumerate(rank_data[start:end], start + 1):
            animated = "a" if emoji["animated"] else ""
            name = emoji["name"]
            emoji_id = emoji["id"]
            count = emoji["count"]
            embed.add_field(
                name=rank,
                value=f"<{animated}:{name}:{emoji_id}> `{count}`次",
                inline=True,
            )
        return embed

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # 獲取群內的表符 ID
        guild_emojis = await self._guild_emoji_list()
        # 獲取 Mongo 內的表符 ID
        mongo_emojis = await self._mongo_emoji_list()

        # 檢查 Mongo 是否殘存群組已刪除的表符，若有則刪除
        for emo in mongo_emojis:
            if emo not in guild_emojis:
                self._db_delete_emoji(emo)
        # 檢查群組是否有未上傳至 Mongo 的表符，若有則新增
        for emo in guild_emojis:
            if emo not in mongo_emojis:
                self._db_add_emoji(emo)
                continue
            self._db_update_emoji(emo)  # 補正已改名的表符

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: list[discord.Emoji],
        after: list[discord.Emoji],
    ) -> None:
        # 如果不是指定群組，不紀錄
        if guild.id != Bot.main_guild:
            return

        # 變更前數量 > 變更後數量: 刪除表符
        if len(before) > len(after):
            for emo in [_ for _ in before if _ not in after]:
                self._db_delete_emoji(emo)
        # 變更前數量 < 變更後數量: 增加表符
        elif len(before) < len(after):
            for emo in [_ for _ in after if _ not in before]:
                self._db_add_emoji(emo)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # 不是在指定群組內使用，不紀錄
        if not msg.guild or msg.guild.id != Bot.main_guild or msg.author.bot:
            return

        import re

        # 正則找出訊息內使用的所有表符，重複只算一次
        emojis_in_msg = set(re.findall(r"<a?:.*?:(\d*)>", msg.content))
        for emo in emojis_in_msg:
            self.mongo.update(
                {"_id": int(emo)}, {"$inc": {"count": 1}}, upsert=False
            )  # 不符合 query 不自動添加

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        if not self.rank_msg_details or self.rank_msg_details[0] is None:
            return

        if msg == self.rank_msg_details[0]:
            self.rank_msg_details = []

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User
    ) -> None:
        # 忽略來自機器人的 Emoji 添加事件
        if user.bot:
            return
        # 如果之前沒有列出排行，或事件訊息不是排行訊息，忽略
        if not self.rank_msg_details or reaction.message != self.rank_msg_details[0]:
            return
        await reaction.remove(user)

        details = self.rank_msg_details

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

        embed = await self._get_updated_rank_embed()
        await reaction.message.edit(embed=embed)

    @commands.group(name="emoji", aliases=["emo", "e"], invoke_without_command=True)
    async def emoji(self, ctx: commands.Context) -> None:
        await ctx.invoke(self.bot.get_command("emoji rank"))

    @emoji.command(aliases=["r"])
    async def rank(self, ctx: commands.Context) -> None:
        await ctx.message.delete(delay=3)
        # 嘗試刪除之前已送出的排行訊息
        try:
            if self.rank_msg_details and self.rank_msg_details[0] is not None:
                await self.rank_msg_details[0].delete()
        except discord.NotFound:
            print("[Emoji rank] 找不到要刪除的訊息，已略過")
        # 獲取 Mongo 內的統計資料並排序
        db_emo_list = [
            {
                "id": emo["_id"],
                "name": emo["name"],
                "animated": emo["animated"],
                "count": emo["count"],
            }
            for emo in self.mongo.find()
        ]
        ranked_emo_list = sorted(db_emo_list, key=lambda x: x["count"], reverse=True)
        total_page = len(ranked_emo_list) // 12

        # 初始化排行訊息詳情
        self.rank_msg_details = [None, 0, total_page, ranked_emo_list]

        # 取得要傳送的 Embed
        embed = await self._get_updated_rank_embed()
        # 傳送 Embed 並記錄至詳情
        rank_message = await ctx.send(embed=embed)
        self.rank_msg_details[0] = rank_message

        # 添加反應
        await rank_message.add_reaction("<:first_page:806497548343705610>")
        await rank_message.add_reaction("<:prev_page:805002492848767017>")
        await rank_message.add_reaction("<:next_page:805002492525805589>")
        await rank_message.add_reaction("<:last_page:806497548558532649>")

    @emoji.command()
    async def reset(self, ctx: commands.Context) -> None:
        # 只有擁有者可執行
        if not (await self.bot.is_owner(ctx.author)):
            return

        # 次數設為零，同時補正已更名的表符
        for emo in await self._mongo_emoji_list():
            self.mongo.update(
                {
                    "_id": emo,
                },
                {
                    "$set": {
                        "name": self.bot.get_emoji(emo).name,
                        "count": 0,
                    }
                },
            )
        await MessageUtils.reply_then_delete(ctx, "記錄重置成功", 5)

    @commands.command(aliases=["er"])
    async def emo_rank(self, ctx: commands.Context) -> None:
        # 使舊指令可執行
        await ctx.invoke(self.bot.get_command("emoji rank"))


def setup(bot: ItkBot) -> None:
    bot.add_cog(EmojiRank(bot))
