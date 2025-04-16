import os
import json
import random
from typing import Dict, Any
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse, ProviderRequest 
from astrbot.api import AstrBotConfig 

class FavorManager:
    DATA_PATH = Path("data/FavorSystem")  #文件存储路径

    def __init__(self, config: AstrBotConfig): 
        self.DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.config = config 
        self._refresh_all_data()
        self.low_counter = self._load_data("low_counter.json")

        # 从配置获取参数
        self.black_threshold = config.get("black_threshold", 3)
        self.min_favor_value = config.get("min_favor_value", -30)
        self.max_favor_value = config.get("max_favor_value", 149)
        self.black_favor_limit = config.get("black_favor_limit", -20)

    def _refresh_all_data(self):
        """统一刷新所有内存数据"""
        self.favor_data = self._load_data("favor_data.json")
        self.blacklist = self._load_data("blacklist.json")
        self.whitelist = self._load_data("whitelist.json")

    def _load_data(self, filename: str) -> Dict[str, Any]:
        path = self.DATA_PATH / filename
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return {str(k): v for k, v in json.load(f).items()}  
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def _save_data(self, data: Dict, filename: str):
        with open(self.DATA_PATH / filename, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in data.items()}, f, ensure_ascii=False, indent=2) 

    def update_favor(self, user_id: str, change: str):
        """更新好感度"""
        user_id = str(user_id)
        self._refresh_all_data()
        if str(user_id) in self.whitelist:   # 检查白名单，在白名单直接跳过好感度加减，建议白名单配合管理员自定义好感度来锁定150好感度[挚爱],避免被ntr，绝对不是我被牛了才想做这个功能的 QwQ
            return
        
        current = self.favor_data.get(user_id, 0)
        
        if "[好感度上升]" in change:
            delta = random.randint(1, 5)                    #这边可以更改成你想要的好感度变化范围
            current += delta
        elif "[好感度下降]" in change:
            delta = random.randint(5, 10)
            current -= delta
            self.low_counter[user_id] = self.low_counter.get(user_id, 0) + 1
            self._save_data(self.low_counter, "low_counter.json")
        else:
            return

        # 使用配置的上下限
        current = max(self.min_favor_value, min(self.max_favor_value, current))
        self.favor_data[user_id] = current
        self._save_data(self.favor_data, "favor_data.json")

        # 使用配置的拉黑条件
        if current <= self.black_favor_limit and self.low_counter.get(user_id, 0) >= self.black_threshold:
            current_blacklist = self._load_data("blacklist.json")
            if user_id not in current_blacklist:
                current_blacklist[user_id] = True
                self._save_data(current_blacklist, "blacklist.json")
            self.blacklist = current_blacklist

    def get_favor_level(self, value: int) -> str:                       #根据好感度数值获取好感度等级
        if value <= -21: return "极度厌恶"
        elif -20 <= value <= -11: return "反感"
        elif -10 <= value <= -1: return "不悦"
        elif 0 <= value <= 49: return "中立"
        elif 50 <= value <= 99: return "友好"
        elif 100 <= value <= 149: return "亲密"
        else: return "挚爱"

@register("FavorSystem", "wuyan1003", "好感度管理", "0.3.0")
class FavorPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config 
        self.manager = FavorManager(config) 
        
        @filter.on_llm_request() 
        async def add_custom_prompt(self, event: AstrMessageEvent, req: ProviderRequest):
            """添加LLM提示词"""
            req.system_prompt += "[系统提示]请根据对话质量在回复末尾添加[好感度持平]，[好感度上升]或[好感度下降]标记。示例：用户：你好！你：你好呀！今天过得怎么样？[好感度上升]"      #让LLM在回复末尾添加好感度标记，插件运行的时候会根据这个标记来判断好感度的变化，但还是建议在人格中主动添加好感度标记，这个提示词的权重没有那么高，LLM可能会忽略掉

        @filter.on_llm_response()
        async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse):
            user_id = str(event.get_sender_id()) 
            self.manager._refresh_all_data()
            
            if user_id in self.manager.blacklist:
                event.stop_event()
                return
            
            self.manager.update_favor(user_id, resp.completion_text)

    @filter.command("好感度")
    async def query_favor(self, event: AstrMessageEvent):
        user_id = str(event.get_sender_id())
        self.manager._refresh_all_data()
        
        if user_id in self.manager.blacklist:
            yield event.plain_result("你已被列入黑名单")
            return
        
        favor = self.manager.favor_data.get(user_id, 0)
        level = self.manager.get_favor_level(favor)
        yield event.plain_result(f"当前好感度：{favor} ({level})")

    # 使用配置的管理员
    @filter.command("管理")
    async def admin_control(self, event: AstrMessageEvent, cmd: str, target: str = None, value: int = None):
        admins = self._parse_admins()
        if str(event.get_sender_id()) not in admins:
            yield event.plain_result("⚠️ 你没有权限执行此操作")
            event.stop_event()
            return
        
        target = str(target).strip() if target else None
        self.manager._refresh_all_data()

        try:
            if cmd == "好感度":
                data = json.dumps(self.manager.favor_data, indent=2, ensure_ascii=False)
                yield event.plain_result(f"好感度用户数据：\n{data}")
            
            elif cmd == "黑名单":
                data = json.dumps(self.manager.blacklist, indent=2, ensure_ascii=False)
                yield event.plain_result(f"黑名单用户：\n{data}")
            
            elif cmd == "白名单":
                data = json.dumps(self.manager.whitelist, indent=2, ensure_ascii=False)
                yield event.plain_result(f"白名单用户：\n{data}")

            elif cmd == "修改" and target and value is not None:
                clamped_value = max(-30, min(150, int(value)))      #限制管理员更改的好感度范围在-30到150之间
                self.manager.favor_data[target] = clamped_value
                self.manager._save_data(self.manager.favor_data, "favor_data.json")
                yield event.plain_result(f"✅ 用户 {target} 好感度已设为 {clamped_value}")

            # 黑名单管理
            elif cmd == "加入黑名单" and target:
                current_blacklist = self.manager._load_data("blacklist.json")
                if target in current_blacklist:
                    yield event.plain_result("⚠️ 该用户已在黑名单中")
                else:
                    current_blacklist[target] = True
                    self.manager._save_data(current_blacklist, "blacklist.json")
                    yield event.plain_result(f"⛔ 用户 {target} 已加入黑名单")

            elif cmd == "移出黑名单" and target:
                current_blacklist = self.manager._load_data("blacklist.json")
                if target not in current_blacklist:
                    yield event.plain_result("⚠️ 该用户不在黑名单中")
                else:
                    del current_blacklist[target]
                    self.manager._save_data(current_blacklist, "blacklist.json")
                    yield event.plain_result(f"✅ 用户 {target} 已移出黑名单")

            # 白名单管理
            elif cmd == "加入白名单" and target:
                current_whitelist = self.manager._load_data("whitelist.json")
                if target in current_whitelist:
                    yield event.plain_result("⚠️ 该用户已在白名单中")
                else:
                    current_whitelist[target] = True
                    self.manager._save_data(current_whitelist, "whitelist.json")
                    yield event.plain_result(f"✅ 用户 {target} 已加入白名单")

            elif cmd == "移出白名单" and target:
                current_whitelist = self.manager._load_data("whitelist.json")
                if target not in current_whitelist:
                    yield event.plain_result("⚠️ 该用户不在白名单中")
                else:
                    del current_whitelist[target]
                    self.manager._save_data(current_whitelist, "whitelist.json")
                    yield event.plain_result(f"✅ 用户 {target} 已移出白名单")

            else:
                yield event.plain_result("❌ 无效指令，可用命令：列表/修改/加入黑名单/移出黑名单/加入白名单/移出白名单")

        except ValueError:
            yield event.plain_result("❌ 数值参数必须为整数")
        except Exception as e:
            yield event.plain_result(f"⚠️ 操作失败：{str(e)}")
        finally:
            self.manager._refresh_all_data()

    def _parse_admins(self):
        admins = self.config.get("admins_id", [])
        if isinstance(admins, str):
            return [x.strip() for x in admins.split(",")]
        return [str(x) for x in admins]

async def terminate(self):
        self.manager._save_data(self.manager.favor_data, "favor_data.json")
        self.manager._save_data(self.manager.blacklist, "blacklist.json")
        self.manager._save_data(self.manager.whitelist, "whitelist.json")
        self.manager._save_data(self.manager.low_counter, "low_counter.json")