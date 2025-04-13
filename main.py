import os
import json
import random
from typing import Dict, Any
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse

class FavorManager:
    DATA_PATH = Path("data/FavorSystem") # 数据存储路径
    
    def __init__(self):
        self.DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.favor_data = self._load_data("favor_data.json")
        self.blacklist = self._load_data("blacklist.json")
        self.low_counter = {}  # 记录连续低好感次数

    def _load_data(self, filename: str) -> Dict[str, Any]:
        path = self.DATA_PATH / filename
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_data(self, data: Dict, filename: str):
        with open(self.DATA_PATH / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_favor(self, user_id: str, change: str):
        """更新好感度"""
        self.favor_data = self._load_data("favor_data.json")
        self.blacklist = self._load_data("blacklist.json")
        
        current = self.favor_data.get(user_id, 0)
        
        if "[好感度上升]" in change:
            delta = random.randint(1, 5)
            current += delta
        elif "[好感度下降]" in change:
            delta = random.randint(5, 10)
            current -= delta
            self.low_counter[user_id] = self.low_counter.get(user_id, 0) + 1
        else:
            return

        # 限制好感度范围
        current = max(-30, min(150, current))
        self.favor_data[user_id] = current
        self._save_data(self.favor_data, "favor_data.json")

        # 自动黑名单逻辑
        if current <= -20 and self.low_counter.get(user_id, 0) >= 3:    # 这里可以更改多少次低好感度加入黑名单，以及多少算低，好感默认3次
            current_blacklist = self._load_data("blacklist.json")
            if str(user_id) not in current_blacklist:
                current_blacklist[str(user_id)] = True
                self._save_data(current_blacklist, "blacklist.json")
            self.blacklist = current_blacklist  # 同步内存数据

    def get_favor_level(self, value: int) -> str:
        """获取好感度阶段"""
        if value <= -21: return "极度厌恶"
        elif -20 <= value <= -11: return "反感"
        elif -10 <= value <= -1: return "不悦"
        elif 0 <= value <= 49: return "中立"
        elif 50 <= value <= 99: return "友好"
        elif 100 <= value <= 149: return "亲密"
        else: return "挚爱"

@register("FavorSystem", "wuyan1003", "好感度管理", "0.1.3")
class FavorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.manager = FavorManager()
        
        # 注册LLM响应钩子
        @filter.on_llm_response()
        async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse):
            user_id = event.get_sender_id()
            # 实时检查黑名单
            current_blacklist = self.manager._load_data("blacklist.json")
            if user_id in current_blacklist:
                event.stop_event()
                return
            
            self.manager.update_favor(user_id, resp.completion_text)

    @filter.command("好感度")
    async def query_favor(self, event: AstrMessageEvent):
        """查询自己的好感度"""
        user_id = event.get_sender_id()
        current_blacklist = self.manager._load_data("blacklist.json")
        if user_id in current_blacklist:
            yield event.plain_result("你已被列入黑名单")
            return
        
        self.manager.favor_data = self.manager._load_data("favor_data.json")
        favor = self.manager.favor_data.get(user_id, 0)
        level = self.manager.get_favor_level(favor)
        yield event.plain_result(f"当前好感度：{favor} ({level})")

    @filter.command("admin")
    async def admin_control(self, event: AstrMessageEvent, cmd: str, target: str = None, value: int = None):
        """管理员指令"""
        if event.get_sender_id() != "114514":          # 替换为管理员ID
            yield event.plain_result("⚠️ 你没有权限执行此操作")
            event.stop_event()
            return

        # 类型统一处理
        target = str(target).strip() if target else None

        # 强制加载最新数据
        self.manager.favor_data = self.manager._load_data("favor_data.json")
        self.manager.blacklist = self.manager._load_data("blacklist.json")

        try:
            if cmd == "list":
                data = json.dumps(self.manager.favor_data, indent=2, ensure_ascii=False)
                yield event.plain_result(f"所有用户数据：\n{data}")

            elif cmd == "modify" and target and value is not None:
                clamped_value = max(-30, min(150, int(value)))
                self.manager.favor_data[target] = clamped_value
                self.manager._save_data(self.manager.favor_data, "favor_data.json")
                self.manager.favor_data = self.manager._load_data("favor_data.json")
                yield event.plain_result(f"✅ 用户 {target} 好感度已设为 {clamped_value}")

            elif cmd == "add_black" and target:
                current_blacklist = self.manager._load_data("blacklist.json")
                if target in current_blacklist:
                    yield event.plain_result("⚠️ 该用户已在黑名单中")
                else:
                    current_blacklist[target] = True
                    self.manager._save_data(current_blacklist, "blacklist.json")
                    self.manager.blacklist = current_blacklist
                    yield event.plain_result(f"⛔ 用户 {target} 已加入黑名单")

            elif cmd == "remove_black" and target:
                current_blacklist = self.manager._load_data("blacklist.json")
                if target not in current_blacklist:
                    yield event.plain_result("⚠️ 该用户不在黑名单中")
                else:
                    del current_blacklist[target]
                    self.manager._save_data(current_blacklist, "blacklist.json")
                    self.manager.blacklist = current_blacklist
                    yield event.plain_result(f"✅ 用户 {target} 已移出黑名单")

            else:
                yield event.plain_result("❌ 无效指令，可用命令：list/add_black/remove_black/modify")

        except ValueError:
            yield event.plain_result("❌ 数值参数必须为整数")
        except Exception as e:
            yield event.plain_result(f"⚠️ 操作失败：{str(e)}")
        finally:
            # 最终数据同步
            self.manager.favor_data = self.manager._load_data("favor_data.json")
            self.manager.blacklist = self.manager._load_data("blacklist.json")

    async def terminate(self):
        """关闭时保存数据"""
        self.manager._save_data(self.manager.favor_data, "favor_data.json")
        self.manager._save_data(self.manager.blacklist, "blacklist.json")