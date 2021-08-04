import re
from typing import Any

import discord
from bot import ItkBot
from bot.configs import Bot, Colors, Emojis, Reactions
from bot.core import CogInit
from bot.utils import MessageUtils
from discord.ext import commands
from saucenao_api import SauceNao, errors


class ImgSearch(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sn = SauceNao(Bot.sauce_nao_key, dbmask=1666715746400, numres=3)
        self.IMG_LINK_PATTERN = re.compile(
            r"(https?:\/\/[^\s]*(\?format=\w*&name=\d*x\d*|(\.png|\.jpg|\.jpeg)))"
        )

        self.result_list = {}
        self.reaction_emos = {
            r: i for i, r in enumerate(Reactions.numbers + Reactions.letters)
        }

    @staticmethod
    def _isfloat(param: Any) -> bool:
        try:
            float(param)
            return True
        except ValueError:
            return False

    def _get_result_embed(
        self, i: int, res: dict[str, Any], remain: int
    ) -> discord.Embed:
        embed = discord.Embed(title="搜尋結果", color=Colors.blue)
        # Footer
        embed.set_footer(
            text=f"第 {i} 張圖｜24h 內剩餘可用次數: {remain}", icon_url=self.bot.user.avatar_url
        )
        # Thumbnail
        if res.thumbnail:
            embed.set_thumbnail(url=res.thumbnail)
        # Fields
        # 作品標題
        if res.title:
            embed.add_field(name="標題", value=res.title)
        # 作者
        if res.author:
            embed.add_field(name="作者", value=res.author)
        # 相似度
        if res.similarity:
            embed.add_field(name="相似度", value=res.similarity, inline=False)
        # 作品連結
        if res.urls:
            for i, url in enumerate(res.urls, 1):
                embed.add_field(name=f"連結{i}", value=url, inline=False)
        # 連結來源
        if "source" in res.raw["data"] and res.raw["data"]["source"]:
            embed.add_field(name="來源", value=res.raw["data"]["source"], inline=False)
        return embed

    def _get_no_result_embed(self, i: int, img_url: str, remain: int) -> discord.Embed:
        embed = discord.Embed(title="搜尋結果", color=Colors.red)
        # Footer
        embed.set_footer(
            text=f"第 {i} 張圖｜24h 內可使用次數: {remain}", icon_url=self.bot.user.avatar_url
        )
        # Thumbnail
        embed.set_thumbnail(url=img_url)
        # Fields
        embed.add_field(name="沒有結果...", value=f"我...我也沒辦法... {Emojis.pepe_hands}")

        return embed

    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User
    ) -> None:
        # 忽略機器人的反應添加事件
        if user.bot:
            return
        # 如果沒有結果訊息紀錄，或不是結果訊息，略過
        if not self.result_list or reaction.message.id not in self.result_list:
            return

        await reaction.remove(user)
        raw_reaction = str(reaction.emoji)
        # 如果不是指定的反應表符，略過
        if raw_reaction not in self.reaction_emos:
            return

        # 反應所代表的數字小於結果串列長度
        if self.reaction_emos[raw_reaction] < len(
            self.result_list[reaction.message.id]
        ):
            await reaction.message.edit(
                content=reaction.message.content,
                embed=self.result_list[reaction.message.id][
                    self.reaction_emos[raw_reaction]
                ],
            )

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        if not self.result_list:
            return

        if msg.id in self.result_list:
            del self.result_list[msg.id]

    @commands.command(aliases=["is"])
    async def image_search(self, ctx: commands.Context, *args) -> None:
        try:
            # 確認是否有指定最低相似度
            last_isfloat = self._isfloat(args[-1]) if args else False
            min_similarity = float(args[-1]) if (args and last_isfloat) else 72

            queue = []
            # 若有回覆訊息，先抓取回覆訊息內附件、圖片連結
            if ctx.message.reference:
                ref_msg = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                queue += [a.url for a in ref_msg.attachments] + [
                    a[0] for a in re.findall(self.IMG_LINK_PATTERN, ref_msg.content)
                ]
            # 若有上傳附件，獲取訊息內圖片連結
            if ctx.message.attachments:
                queue += [a.url for a in ctx.message.attachments]
            # 若有附上圖片連結，抓取訊息內圖片連結
            if args[:-1] if last_isfloat else args:
                queue += [
                    a
                    for a in (args[:-1] if last_isfloat else args)
                    if re.match(self.IMG_LINK_PATTERN, a)
                ]
            # 執行至此佇列仍為空，判定為未給予搜尋要素
            if not queue:
                raise NoImageToQuery

            result_embeds = []
            # 最多僅搜尋佇列前 6
            for i, img_url in enumerate(queue[:6], 1):
                at_least_one_result = False

                results = self.sn.from_url(url=img_url)
                for res in results:
                    # 相似度小於指定相似度，略過
                    if res.similarity < min_similarity:
                        continue

                    at_least_one_result = True
                    # 獲取結果 Embed
                    result_embeds.append(
                        self._get_result_embed(i, res, results.long_remaining)
                    )
                # 完全沒有高於指定相似度的結果
                if not at_least_one_result:
                    # 獲取無結果 Embed
                    result_embeds.append(
                        self._get_no_result_embed(i, img_url, results.long_remaining)
                    )
            # 送出搜尋結果訊息
            result_msg = await MessageUtils.reply_then_delete(
                ctx, "", 240, embed=result_embeds[0]
            )
            # 添加搜尋結果訊息
            self.result_list[result_msg.id] = result_embeds
            # 添加反應
            for i in range(len(result_embeds)):
                await result_msg.add_reaction(list(self.reaction_emos.keys())[i])

        except errors.UnknownApiError:
            await MessageUtils.reply_then_delete(
                ctx, f"嗚呼，搜圖 API 爆掉了 {Emojis.pepe_hypers}"
            )
        except errors.UnknownServerError:
            await MessageUtils.reply_then_delete(
                ctx, f"搜圖伺服器爆掉了，窩無能為力 {Emojis.pepe_depressed}"
            )
        except errors.LongLimitReachedError:
            await MessageUtils.reply_then_delete(
                ctx, f"今天的搜尋次數已達上限 {Emojis.pepe_hands}"
            )
        except NoImageToQuery:
            await MessageUtils.reply_then_delete(ctx, f"你是不是沒有放上要找的圖 {Emojis.thonk}")


class NoImageToQuery(Exception):
    pass


def setup(bot: ItkBot) -> None:
    bot.add_cog(ImgSearch(bot))
