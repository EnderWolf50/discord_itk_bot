import asyncio
import random
from datetime import datetime as dt
from datetime import timedelta
from typing import Any, Union

import discord
from bot import ItkBot
from bot.core import CogInit
from discord.ext import commands


class AbGame(CogInit):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._ongoing_games = {}

    @staticmethod
    def _get_ab_count(
        num_list: list[int], ans_list: list[int], ans_len: int
    ) -> tuple[int, int]:
        a_count = 0
        b_count = 0
        for i in range(ans_len):
            for j in range(ans_len):
                if i != j:
                    # 發現重複數字，回傳長度 + 1 作為錯誤
                    if num_list[i] == num_list[j]:
                        return ans_len + 1, ans_len + 1
                    elif num_list[i] == ans_list[j]:
                        b_count += 1
                elif num_list[i] == ans_list[j]:
                    a_count += 1
        return a_count, b_count

    @staticmethod
    def _get_time_taken_str(time: dt) -> str:
        time_taken = (dt.utcnow() - time).total_seconds()
        h, r = divmod(time_taken, 3600)
        m, s = divmod(r, 60)
        return f"{h:02.0f}:{m:02.0f}:{s:02.0f}"

    async def _clean_game_messages(
        self,
        channel: Union[discord.TextChannel, discord.DMChannel],
        game_info: dict[str, Any],
    ) -> None:
        if isinstance(channel, discord.DMChannel):
            for msg in game_info["msg_delete_queue"]:
                await (await channel.fetch_message(msg)).delete()
            return

        def in_queue(m) -> bool:
            return m.id in game_info["msg_delete_queue"]

        await channel.purge(limit=None, after=game_info["start_time"], check=in_queue)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # 檢查是否有正在進行的遊戲紀錄
        if msg.channel.id not in self._ongoing_games:
            return
        # 忽略機器人事件
        if msg.author == self.bot.user:
            return

        game_info = self._ongoing_games[msg.channel.id]
        ans_len = game_info["ans_len"]
        ans = game_info["ans"]

        content = msg.content
        res_msg = None
        if content.isdigit() and len(content) == ans_len:
            a_count, b_count = self._get_ab_count(list(content), ans, ans_len)
            # 如果回傳值皆大於答案長度，為輸入重複數字
            if a_count > ans_len or b_count > ans_len:
                res_msg = await msg.reply(f"請勿輸入重複的數字！｜答案長度：{ans_len}")
            # A 數量等於答案長度即為答對
            elif a_count == ans_len:
                # 刪除遊戲資訊
                del self._ongoing_games[msg.channel.id]

                await msg.reply(
                    f"（{content}）：**{a_count}A{b_count}B**\n"
                    f"恭喜 {msg.author.mention} 答對了！｜"
                    f"遊戲總時長：{self._get_time_taken_str(game_info['start_time'])}"
                )
                # 提早跳出函式（避免發送提示訊息及記錄）
                await asyncio.sleep(5)
                await self._clean_game_messages(msg.channel, game_info)
                return
            # 提示玩家目前進度
            else:
                res_msg = await msg.reply(
                    f"（{content}）：**{a_count}A{b_count}B**｜答案長度：{ans_len}"
                )
            # 紀錄回覆訊息
            game_info["msg_delete_queue"].append(res_msg.id)
            # 如果是在群組端遊玩，額外記錄猜測訊息
            if msg.guild:
                game_info["msg_delete_queue"].append(msg.id)

    @commands.group(name="ab")
    async def ab(self, ctx: commands.Context) -> None:
        # 僅用作 Group 用途
        pass

    @ab.command(aliases=["s"])
    async def start(self, ctx: commands.Context, answer_length: int = 4) -> None:
        # 指定長度確認
        if not 1 <= answer_length <= 10:
            await ctx.reply("謎題的長度必須介於 1 ~ 10 個字之間", delete_after=7)
        # 未被記錄等於未開始遊戲
        elif ctx.channel not in self._ongoing_games:
            self._ongoing_games[ctx.channel.id] = {
                "start_time": ctx.message.created_at - timedelta(seconds=1),
                "ans_len": answer_length,
                "ans": random.sample("1234567890", answer_length),
                "msg_delete_queue": [(await ctx.send(f"請輸入 {answer_length} 位不同數字")).id],
            }
        await ctx.message.delete(delay=7)

    @ab.command(aliases=["e"])
    async def end(self, ctx: commands.Context) -> None:
        # 確認頻道是否有正在進行的遊戲
        if ctx.channel.id not in self._ongoing_games:
            await ctx.reply("這個頻道沒有進行中的遊戲喔", delete_after=7)
        else:
            # 獲得遊戲資訊並刪除
            game_info = self._ongoing_games[ctx.channel.id]
            del self._ongoing_games[ctx.channel.id]

            ans = "".join(game_info["ans"])
            await ctx.reply(
                f"{ctx.author.mention} 結束了遊戲!\n正確答案為 **{ans}**！｜"
                f"遊戲總時長：{self._get_time_taken_str(game_info['start_time'])}"
            )
            await asyncio.sleep(5)
            await self._clean_game_messages(ctx.channel, game_info)
        await ctx.message.delete(delay=7)

    @commands.command(aliases=["ab_s"])
    async def ab_start(self, ctx: commands.Context, answer_length: int = 4) -> None:
        # 使舊指令可執行
        await ctx.invoke(self.bot.get_command("ab start"), answer_length=answer_length)

    @commands.command(aliases=["ab_e"])
    async def ab_end(self, ctx: commands.Context) -> None:
        # 使舊指令可執行
        await ctx.invoke(self.bot.get_command("ab end"))


def setup(bot: ItkBot) -> None:
    bot.add_cog(AbGame(bot))
