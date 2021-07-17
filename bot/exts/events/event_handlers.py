import logging
import random
import re
from datetime import timedelta
from itertools import cycle
from pathlib import Path
from typing import Any

import discord
from bot import ItkBot
from bot.configs import Bot, Emojis, Events
from bot.core import CogInit
from discord.ext import commands
from googleapiclient import discovery, errors

logger = logging.getLogger(__name__)


class EventHandlers(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.backup_path = Path(Bot.image_folder, "backup")
        self.backup_path.mkdir(exist_ok=True)

        self.google_search_api_keys = cycle(Bot.google_search_api_keys)

    def _is_command(self, string: str) -> bool:
        return string.lower()[1:].split(" ")[0] in self.bot.ignore_kw_list

    def google_search(self, q: str, **kwargs) -> dict[str, Any]:
        key = next(self.google_search_api_keys)
        cse = Bot.custom_search_engine_id
        try:
            service = discovery.build("customsearch", "v1", developerKey=key)
            res = (
                service.cse()
                .list(q=q, cx=cse, **Bot.google_search_options, **kwargs)
                .execute()
            )

            return res.get("items", None)
        except errors.HttpError:
            logger.error(f"使用 {key} 進行搜索時發生錯誤，可能是超出配額或或金鑰無效")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # 忽略指定頻道
        if msg.channel and msg.channel.id in Bot.ignore_channels:
            return

        author = msg.author
        author_name = author.display_name.lower()
        content = msg.content.lower()

        # Reaction
        if "ㄐㄐ" in content:
            await msg.add_reaction("\N{AUBERGINE}")
        if "雞雞" in content:
            await msg.add_reaction("<:emoji_101:713997954201157723>")
        if "尻尻" in content:
            await msg.add_reaction("<a:emoji_103:713998749680009250>")
        if "<:095:802993480632631316>" in content:
            await msg.reply(Events.helen_art)

        if msg.author.bot:
            return

        # mentions = [u.display_name for u in msg.mentions]
        # 提及機器人
        if self.bot.user in msg.mentions and not self._is_command(content):
            await msg.reply(random.choice(Events.mentioned_reply))
        # 窩不知道
        elif any(kw in content for kw in ("窩不知道", "我不知道", "idk")):
            images = [i[0] for i in Events.idk]
            weights = [i[1] for i in Events.idk]

            pic = random.choices(images, weights=weights)[0]

            if pic.endswith(".gif"):
                await msg.reply(file=discord.File(pic), delete_after=20)
            else:
                await msg.reply(file=discord.File(pic), delete_after=7)
        # 讀取貓咪
        elif any(kw in content for kw in ("ldc", "痾")):
            await msg.channel.send(Events.loading_cat[0])
            await msg.channel.send(Events.loading_cat[1])
            await msg.channel.send(Events.loading_cat[2])
        # 六點
        elif any(kw in content for kw in ("......", "六點", "抱歉")):
            await msg.reply(Emojis.i11_chiwawa)
        # 素每
        elif any(kw in content for kw in ("熱", "好熱", "素每")):
            pic = discord.File(random.choice(Events.so_hot))
            await msg.reply(file=pic, delete_after=7)
        # 唐立淇
        elif any(kw in content for kw in ("星座", "唐綺陽", "唐立淇")):
            pic = discord.File(Events.tang)
            await msg.reply(file=pic, delete_after=7)
        # 撒嬌 (訊息)
        elif any(kw in content for kw in ("donut", "bakery", "撒嬌")):
            if random.randint(0, 4) == 4:
                await msg.reply("還敢撒嬌阿")
            else:
                await msg.reply(random.choice(Events.act_cute))
        # 撒嬌 (名稱)
        elif any(kw in author_name for kw in ("donut", "bakery", "撒嬌")):
            await msg.add_reaction(random.choice(Events.act_cute))
        # 神奇海螺
        elif "神奇海螺" in content and content[:2] != "請問":
            pic = discord.File(random.choice(Events.magic_conch.kw))
            await msg.reply(file=pic, delete_after=7)
        # 菊
        elif "菊" in content:
            pic = discord.File(Events.chen)
            await msg.reply(file=pic, delete_after=7)
        # 海倫
        elif "海倫" in content:
            pic = discord.File(random.choice(Events.helen_cards))
            await msg.reply(file=pic, delete_after=7)
        # 好色
        elif "好色" in content:
            pic = discord.File(Events.ck_lewd)
            await msg.reply(file=pic, delete_after=7)
        # 假的
        elif "假的" in content:
            pic = discord.File(Events.fake)
            await msg.reply(file=pic, delete_after=7)
        # 很壞
        elif "很壞" in content:
            pic = discord.File(Events.you_bad)
            await msg.reply(file=pic, delete_after=7)
        # 好耶
        elif "好耶" in content:
            pic = discord.File(random.choice(Events.yeah))
            await msg.reply(file=pic, delete_after=7)
        # 陷阱卡
        elif "陷阱卡" in content:
            pic = discord.File(Events.trap_card)
            await msg.reply(file=pic, delete_after=7)
        # 交朋友
        elif "交朋友" in content:
            pic = discord.File(random.choice(Events.make_friends))
            await msg.reply(file=pic, delete_after=7)
        # 怕
        elif "怕" in content:
            pic = discord.File(Events.scared)
            await msg.reply(file=pic, delete_after=7)
        # 很嗆是吧
        elif re.search(r"很嗆(?:是吧|[喔欸])?|嗆[喔欸]", content):
            pic = discord.File(Events.flaming)
            await msg.reply(file=pic, delete_after=7)
        # 請問
        if content.startswith("請問"):
            if content[2:4] == "晚餐":
                await msg.reply(random.choice(Events.meals))
            elif content[2:6] == "神奇海螺":
                pic = discord.File(random.choice(Events.magic_conch.ask))
                await msg.reply(file=pic, delete_after=7)
            else:
                result = self.google_search(content[2:], num=1)
                if result is None:
                    await msg.reply(
                        f"很遺憾\n你問的東西連 Google 都回答不了你 {Emojis.pepe_coffee}",
                        delete_after=10,
                    )
                    await msg.delete(delay=10)
                    return
                await msg.reply(result[0]["link"], delete_after=30)

        # 圖片備份
        counter = 0
        for attachment in msg.attachments:
            if any(
                attachment.filename.lower().endswith(ext)
                for ext in (".jpg", ".jpeg", ".png", ".gif")
            ):
                counter += 1
                ext = attachment.filename.split(".")[1]
                await attachment.save(
                    self.backup_path / Path(f"{msg.id}_{counter:02d}.{ext}")
                )

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        # 忽略頻道
        if after.channel and after.channel.id in Bot.ignore_channels:
            return
        # 忽略機器人
        if after.author.bot:
            return
        # 忽略私訊及測試群組
        if not after.guild or after.guild.id == Bot.test_guild:
            return
        # 前後訊息內容相同，略過
        if before.content.lower() == after.content.lower():
            return

        author = after.author
        channel = after.channel
        create_time = (after.edited_at + timedelta(hours=8)).strftime(
            "%Y/%m/%d %H:%M:%S"
        )
        # 尋找已備份的圖片檔
        files = [
            f for f in self.backup_path.iterdir() if f.name.startswith(str(after.id))
        ]
        await self.bot.get_channel(Bot.edit_backup_channel).send(
            f"{author.display_name} `{author.id}`｜{channel.name} `{create_time}`\n"
            f"{before.content} `→` {after.content}",
            files=[discord.File(file) for file in files],
        )

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        # 忽略機器人
        if msg.author.bot:
            return
        # 忽略私訊及測試群組
        if not msg.guild or msg.guild.id == Bot.test_guild:
            return
        # 忽略指令
        if self._is_command(msg.content):
            return

        # 無限讀取貓咪
        if any(
            kw in msg.content
            for kw in (
                Events.loading_cat[0],
                Events.loading_cat[1],
                Events.loading_cat[2],
            )
        ):
            await msg.channel.send(Events.loading_cat[0])
            await msg.channel.send(Events.loading_cat[1])
            await msg.channel.send(Events.loading_cat[2])

        author = msg.author
        channel = msg.channel
        create_time = (msg.created_at + timedelta(hours=8)).strftime(
            "%Y/%m/%d %H:%M:%S"
        )
        # 尋找已備份的圖片檔
        files = [
            f for f in self.backup_path.iterdir() if f.name.startswith(str(msg.id))
        ]
        await self.bot.get_channel(Bot.chat_backup_channel).send(
            f"{author.display_name} `{author.id}`｜{channel.name} `{create_time}`\n"
            f"{msg.content}",
            files=[discord.File(file) for file in files],
        )
        # 刪除圖片
        for file in files:
            file.unlink()

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User
    ) -> None:
        # 取消對貓貓分屍的行為
        if any(
            kw in reaction.message.content
            for kw in (
                Events.loading_cat[0],
                Events.loading_cat[1],
                Events.loading_cat[2],
            )
        ):
            await reaction.message.remove_reaction(reaction, user)


def setup(bot: ItkBot) -> None:
    bot.add_cog(EventHandlers(bot))
