import asyncio
import json
import random
import re
from pathlib import Path
from typing import Dict, Set
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse

# 好感度阶段配置
FRIENDLY_STAGES = {
    -30: "极度厌恶",
    0: "反感",
    20: "不悦",
    50: "中立",
    80: "友好",
    110: "亲密",
    150: "挚爱"
}

class FavorSystem:
    def __init__(self):
        self.data_path = Path("data/favor_system")
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.favor_data = self._load_data("favor.json")
        self.blacklist = self._load_data("blacklist.json")
        self.negative_records = self._load_data("negative_records.json")
        self.lock = asyncio.Lock()

    def _load_data(self, filename: str) -> Dict:
        try:
            with open(self.data_path / filename) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_data(self, data: Dict, filename: str):
        with open(self.data_path / filename, 'w') as f:
            json.dump(data, f, indent=2)

    async def update_favor(self, user_id: str, change: str):
        async with self.lock:
            current = self.favor_data.get(user_id, 50)  # 默认中立
            if change == "上升":
                current += random.randint(1, 5)
            elif change == "下降":
                current -= random.randint(5, 10)
            
            # 边界控制
            current = max(-30, min(current, 150))
            self.favor_data[user_id] = current
            
            # 记录负面次数
            if change == "下降":
                self.negative_records[user_id] = self.negative_records.get(user_id, 0) + 1
                if self.negative_records[user_id] >= 3:  # 连续3次负面
                    self.blacklist[user_id] = True
            else:
                self.negative_records[user_id] = 0
            
            self._save_data(self.favor_data, "favor.json")
            self._save_data(self.blacklist, "blacklist.json")
            self._save_data(self.negative_records, "negative_records.json")

    def get_stage(self, favor: int) -> str:
        for threshold in sorted(FRIENDLY_STAGES.keys(), reverse=True):
            if favor >= threshold:
                return FRIENDLY_STAGES[threshold]
        return "未知状态"

@register("FavorSystem", "作者", "好感度管理系统", "1.0.0")
class FavorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.system = FavorSystem()
        
        # 注册LLM响应钩子
        @filter.on_llm_response()
        async def handle_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
            if event.get_sender_id() in self.system.blacklist:
                event.stop_event()
                return

            # 解析好感度标记
            if match := re.search(r'\[好感度(上升|下降)\]', resp.completion_text):
                user_id = event.get_sender_id()
                await self.system.update_favor(user_id, match.group(1))

        # 注册指令
        @filter.command("好感度")
        async def query_favor(self, event: AstrMessageEvent):
            user_id = event.get_sender_id()
            favor = self.system.favor_data.get(user_id, 50)
            stage = self.system.get_stage(favor)
            yield event.plain_result(
                f"当前好感度：{favor}\n"
                f"关系阶段：{stage}"
            )

        @filter.command("黑名单", permission=filter.PermissionType.ADMIN)
        async def show_blacklist(self, event: AstrMessageEvent):
            blacklist = "\n".join(self.system.blacklist.keys())
            yield event.plain_result(f"黑名单用户：\n{blacklist or '暂无'}")

    async def terminate(self):
        pass