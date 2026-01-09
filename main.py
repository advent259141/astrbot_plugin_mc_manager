"""
AstrBot MC服务器管理插件
通过LLM智能管理Minecraft服务器，支持Fabric/Forge/NeoForge
"""

import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api import AstrBotConfig, logger
from astrbot.core.provider.entities import LLMResponse

from .rcon_client import MinecraftRCON
from .tools import player_tools, game_tools, server_tools, world_tools
from .log_client import LogClient
from .script_executor import ScriptExecutor


@register(
    name="mc_manager",
    desc="通过LLM智能管理Minecraft服务器",
    version="1.0.0",
    author="AstrBot Community"
)
class MCManagerPlugin(Star):
    """Minecraft服务器管理插件"""
    
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        
        # 从配置加载RCON设置
        self.config = config
        
        # 初始化RCON客户端
        self.rcon = MinecraftRCON(
            host=self.config.get("rcon_host", "localhost"),
            port=self.config.get("rcon_port", 25575),
            password=self.config.get("rcon_password", "")
        )
        
        # 加载管理员列表
        self.admin_ids = set(self.config.get("admin_ids", []))
        
        # 是否启用危险命令
        self.enable_dangerous = self.config.get("enable_dangerous_commands", False)
        
        # 唤醒词配置已移除 - 所有消息都提交，由AstrBot框架层唤醒词决定是否调用LLM
        # 旧配置: self.wake_words = self.config.get("wake_words", ["bot"])
        
        # 是否启用聊天响应
        self.enable_chat_response = self.config.get("enable_chat_response", True)
        
        # 加载机器人昵称配置
        self.bot_nickname = self.config.get("bot_nickname", "Bot")
        
        # 加载统一上下文配置
        self.enable_unified_context = self.config.get("enable_unified_context", False)
        self.unified_group_umo = self.config.get("unified_group_umo", "")
        self.mc_message_prefix = self.config.get("mc_message_prefix", "[MC]")
        
        # 初始化日志客户端（如果启用）
        self.log_client = None
        enable_log = self.config.get("enable_log_monitor", False)
        if enable_log:
            log_host = self.config.get("log_server_host", "127.0.0.1")
            log_port = self.config.get("log_server_port", 25576)
            # 所有MC消息都会提交到AstrBot，由框架的wake_prefix控制是否调用LLM
            self.log_client = LogClient(log_host, log_port)
            self.log_client.set_chat_callback(self._on_player_chat)
            self.log_client.set_fake_event_handler(self._send_fake_event)
        
        # 初始化脚本执行器
        self.script_executor = ScriptExecutor()
        
        # 注入RCON客户端到所有工具模块
        self._inject_rcon()
        
        # 注册工具到脚本执行器
        self._register_script_tools()
        
        logger.info(f"MC Manager插件已加载，RCON: {self.config.get('rcon_host')}:{self.config.get('rcon_port')}")
    
    async def initialize(self):
        """插件激活时自动调用 - 启动长连接任务"""
        # 启动日志客户端
        if self.log_client:
            if await self.log_client.connect():
                asyncio.create_task(self.log_client.start_listening())
                logger.info("日志监控已启动")
            else:
                logger.error("日志监控启动失败：无法连接到日志服务器")
    
    def _inject_rcon(self):
        """将RCON客户端注入到所有工具模块"""
        player_tools.set_rcon(self.rcon)
        game_tools.set_rcon(self.rcon)
        server_tools.set_rcon(self.rcon)
        server_tools.set_dangerous_commands_enabled(self.enable_dangerous)
        world_tools.set_rcon(self.rcon)
    
    def _register_script_tools(self):
        """将所有工具函数注册到脚本执行器"""
        # 玩家管理工具
        self.script_executor.register_tool("kick_player", player_tools.kick_player)
        self.script_executor.register_tool("ban_player", player_tools.ban_player)
        self.script_executor.register_tool("pardon_player", player_tools.pardon_player)
        self.script_executor.register_tool("op_player", player_tools.op_player)
        self.script_executor.register_tool("deop_player", player_tools.deop_player)
        self.script_executor.register_tool("whitelist_add", player_tools.whitelist_add)
        self.script_executor.register_tool("whitelist_remove", player_tools.whitelist_remove)
        
        # 游戏操作工具
        self.script_executor.register_tool("give_item", game_tools.give_item)
        self.script_executor.register_tool("teleport_player", game_tools.teleport_player)
        self.script_executor.register_tool("set_gamemode", game_tools.set_gamemode)
        self.script_executor.register_tool("kill_entity", game_tools.kill_entity)
        self.script_executor.register_tool("clear_inventory", game_tools.clear_inventory)
        self.script_executor.register_tool("set_experience", game_tools.set_experience)
        
        # 服务器管理工具
        self.script_executor.register_tool("list_players", server_tools.list_players)
        self.script_executor.register_tool("say_message", server_tools.say_message)
        self.script_executor.register_tool("tellraw", server_tools.tellraw)
        self.script_executor.register_tool("title", server_tools.title)
        self.script_executor.register_tool("save_world", server_tools.save_world)
        self.script_executor.register_tool("whitelist_list", server_tools.whitelist_list)
        self.script_executor.register_tool("banlist", server_tools.banlist)
        self.script_executor.register_tool("execute_command", server_tools.execute_command)
        
        # 世界管理工具
        self.script_executor.register_tool("set_weather", world_tools.set_weather)
        self.script_executor.register_tool("set_time", world_tools.set_time)
        self.script_executor.register_tool("set_difficulty", world_tools.set_difficulty)
        self.script_executor.register_tool("set_gamerule", world_tools.set_gamerule)
        self.script_executor.register_tool("summon_entity", world_tools.summon_entity)
        
        logger.info(f"已注册 {len(self.script_executor.tools)} 个工具到脚本执行器")
    
    async def _on_player_chat(self, player: str, message: str, time: str):
        """
        处理玩家聊天消息的回调函数
        
        Args:
            player: 玩家名称
            message: 聊天消息内容
            time: 消息时间
        """
        pass
    
    async def _send_fake_event(self, player: str, message: str):
        """
        提交所有MC消息到AstrBot
        - LTM会记录所有消息作为上下文
        - 只有包含AstrBot配置的唤醒词的消息才会触发LLM
        
        Args:
            player: 玩家名称
            message: 消息内容
        """
        try:
            from astrbot.core.star.star_tools import StarTools
            from astrbot.core.message.components import Plain
            from astrbot.core.platform.astrbot_message import MessageMember
            
            # 如果启用了统一上下文且配置了UMO，从UMO中提取session_id
            # 否则使用默认的 "mc_server_chat"
            if self.enable_unified_context and self.unified_group_umo:
                # UMO格式: platform_id:message_type:session_id
                parts = self.unified_group_umo.split(":")
                mc_session_id = parts[2] if len(parts) == 3 else "mc_server_chat"
                group_id = mc_session_id
            else:
                mc_session_id = "mc_server_chat"
                group_id = "mc_server_chat"
            
            # 使用真实的玩家信息
            sender = MessageMember(
                user_id=f"mc_player_{player}",  # 用玩家名作为ID
                nickname=f"{player}(MC)"  # 显示玩家名和来源
            )
            
            # 构造消息文本 - 格式: [MC] 玩家名: 消息内容
            message_text = f"{self.mc_message_prefix} {player}: {message}"
            
            # 创建新消息对象
            new_message = await StarTools.create_message(
                type="GroupMessage",
                self_id="astrbot_mc_plugin",
                session_id=mc_session_id,
                sender=sender,
                message=[Plain(message_text)],
                message_str=message_text,
                group_id=group_id
            )
            
            # 提交事件到AstrBot
            # - is_wake=True 确保LTM会处理（记录消息）
            # - 是否真正调用LLM由AstrBot框架的唤醒词配置决定
            await StarTools.create_event(
                abm=new_message,
                platform="aiocqhttp",
                is_wake=True
            )
            
            logger.info(f"MC消息已提交: [{player}] {message}")
            
        except Exception as e:
            logger.error(f"提交MC消息失败: {e}")
    
    
    async def terminate(self):
        """插件禁用/重载时自动调用 - 清理资源"""
        # 断开日志客户端
        if self.log_client:
            await self.log_client.disconnect()
            logger.info("日志监控已停止")
    
    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, response: LLMResponse):
        """
        LLM响应后的钩子，用于将响应发送到MC聊天框
        
        Args:
            event: 原始消息事件
            response: LLM的响应
        """
        # 检查是否启用聊天响应功能
        if not self.enable_chat_response:
            return
        
        try:
            # 检查是否来自MC会话（不管是否配置了统一上下文）
            sender_id = event.get_sender_id()
            if sender_id and sender_id.startswith("mc_player_"):
                # 获取响应文本
                response_text = ""
                if response.result_chain:
                    # 从消息链中提取文本
                    response_text = response.result_chain.get_plain_text()
                elif response._completion_text:
                    response_text = response._completion_text
                
                if response_text:
                    # 发送到MC服务器聊天框
                    await self._send_to_mc_chat(response_text)
        except Exception as e:
            logger.error(f"处理LLM响应时出错: {e}")
    
    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """
        装饰结果钩子，用于阻止MC消息的默认回复发送到QQ群
        
        当MC玩家发送消息触发LLM时，清空默认回复，避免自动发送到QQ群
        MC的回复已通过on_llm_response中的_send_to_mc_chat发送
        
        Args:
            event: 消息事件
        """
        # 检查是否是MC玩家的消息
        sender_id = event.get_sender_id()
        if sender_id and sender_id.startswith("mc_player_"):
            # 清空消息链，阻止自动发送到QQ群
            result = event.get_result()
            if result:
                result.chain = []
    
    async def _send_to_mc_chat(self, message: str):
        """
        将消息发送到MC服务器聊天框
        
        Args:
            message: 要发送的消息内容
        """
        try:
            # MC聊天框有长度限制，需要分段发送
            max_length = 200  # 每段最大长度
            
            # 处理换行符，分段发送
            lines = message.split('\n')
            current_chunk = ""
            
            for line in lines:
                # 如果当前行太长，需要进一步拆分
                if len(line) > max_length:
                    # 先发送当前累积的内容
                    if current_chunk:
                        await self._send_single_mc_message(current_chunk)
                        current_chunk = ""
                    
                    # 拆分长行
                    for i in range(0, len(line), max_length):
                        chunk = line[i:i + max_length]
                        await self._send_single_mc_message(chunk)
                else:
                    # 检查添加这行后是否超长
                    test_chunk = current_chunk + ('\n' if current_chunk else '') + line
                    if len(test_chunk) > max_length:
                        # 先发送当前累积的内容
                        if current_chunk:
                            await self._send_single_mc_message(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk = test_chunk
            
            # 发送剩余内容
            if current_chunk:
                await self._send_single_mc_message(current_chunk)
                
        except Exception as e:
            logger.error(f"发送消息到MC聊天框失败: {e}")
    
    async def _send_single_mc_message(self, message: str):
        """
        发送单条消息到MC聊天框
        
        Args:
            message: 消息内容
        """
        try:
            # 转义JSON特殊字符
            escaped_message = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            
            # 使用tellraw命令发送消息给所有玩家
            json_text = f'{{"text":"[{self.bot_nickname}] {escaped_message}", "color":"aqua"}}'
            command = f'tellraw @a {json_text}'
            
            result = await self.rcon.execute_async(command)
        except Exception as e:
            logger.error(f"发送单条消息到MC失败: {e}")
    
    def is_admin(self, user_id: str) -> bool:
        """
        检查用户是否为管理员
        
        Args:
            user_id: 用户ID（QQ号或MC玩家ID，格式：mc_player_{玩家名}）
            
        Returns:
            是否为管理员，如果admin_ids为空则所有人都是管理员
        """
        logger.info(f"权限检查: user_id={user_id}, admin_ids={self.admin_ids}")
        if not self.admin_ids:
            return True
        
        # 检查原始ID（QQ号）
        if str(user_id) in self.admin_ids:
            return True
        
        # 检查MC玩家名（从 mc_player_PlayerName 提取 PlayerName）
        if user_id.startswith("mc_player_"):
            player_name = user_id.replace("mc_player_", "")
            if player_name in self.admin_ids:
                return True
        
    
    def _check_permission(self, event: AstrMessageEvent) -> tuple[bool, str]:
        """
        检查用户是否有权限执行操作
        
        Args:
            event: 消息事件
            
        Returns:
            (是否有权限, 错误消息或空字符串)
        """
        user_id = event.get_sender_id()
        if not self.is_admin(user_id):
            return False, f"权限不足：用户 {user_id} 不在管理员列表中"
        return True, ""

    @filter.llm_tool(name="kick_player")
    async def tool_kick_player(self, event: AstrMessageEvent, player: str, reason: str = "被管理员踢出") -> str:
        """踢出指定玩家
        
        Args:
            player(string): 要踢出的玩家名称
            reason(string): 踢出原因
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.kick_player(player, reason)
    
    @filter.llm_tool(name="ban_player")
    async def tool_ban_player(self, event: AstrMessageEvent, player: str, reason: str = "违反服务器规则") -> str:
        """封禁指定玩家
        
        Args:
            player(string): 要封禁的玩家名称
            reason(string): 封禁原因
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.ban_player(player, reason)
    
    @filter.llm_tool(name="pardon_player")
    async def tool_pardon_player(self, event: AstrMessageEvent, player: str) -> str:
        """解封指定玩家
        
        Args:
            player(string): 要解封的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.pardon_player(player)
    
    @filter.llm_tool(name="op_player")
    async def tool_op_player(self, event: AstrMessageEvent, player: str) -> str:
        """给予玩家OP权限
        
        Args:
            player(string): 要给予OP权限的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.op_player(player)
    
    @filter.llm_tool(name="deop_player")
    async def tool_deop_player(self, event: AstrMessageEvent, player: str) -> str:
        """移除玩家的OP权限
        
        Args:
            player(string): 要移除OP权限的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.deop_player(player)
    
    @filter.llm_tool(name="whitelist_add")
    async def tool_whitelist_add(self, event: AstrMessageEvent, player: str) -> str:
        """将玩家添加到白名单
        
        Args:
            player(string): 要添加到白名单的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.whitelist_add(player)
    
    @filter.llm_tool(name="whitelist_remove")
    async def tool_whitelist_remove(self, event: AstrMessageEvent, player: str) -> str:
        """将玩家从白名单移除
        
        Args:
            player(string): 要从白名单移除的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await player_tools.whitelist_remove(player)
    
    @filter.llm_tool(name="give_item")
    async def tool_give_item(self, event: AstrMessageEvent, player: str, item: str, count: int = 1) -> str:
        """给予玩家物品
        
        Args:
            player(string): 要给予物品的玩家名称
            item(string): 物品ID，如diamond、iron_sword
            count(number): 物品数量，默认1
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await game_tools.give_item(player, item, count)
    
    @filter.llm_tool(name="teleport_player")
    async def tool_teleport_player(self, event: AstrMessageEvent, player: str, target: str) -> str:
        """传送玩家
        
        Args:
            player(string): 要传送的玩家名称
            target(string): 目标位置（坐标如"100 64 200"）或目标玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await game_tools.teleport_player(player, target)
    
    @filter.llm_tool(name="set_gamemode")
    async def tool_set_gamemode(self, event: AstrMessageEvent, player: str, mode: str) -> str:
        """设置玩家游戏模式
        
        Args:
            player(string): 玩家名称
            mode(string): 游戏模式：survival/creative/adventure/spectator
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await game_tools.set_gamemode(player, mode)
    
    @filter.llm_tool(name="kill_entity")
    async def tool_kill_entity(self, event: AstrMessageEvent, target: str) -> str:
        """杀死指定实体
        
        Args:
            target(string): 目标选择器或玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await game_tools.kill_entity(target)
    
    @filter.llm_tool(name="clear_inventory")
    async def tool_clear_inventory(self, event: AstrMessageEvent, player: str, item: str = None) -> str:
        """清空玩家背包
        
        Args:
            player(string): 玩家名称
            item(string): 可选，特定物品ID
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await game_tools.clear_inventory(player, item)
    
    @filter.llm_tool(name="set_experience")
    async def tool_set_experience(self, event: AstrMessageEvent, player: str, amount: int, operation: str = "set", unit: str = "points") -> str:
        """设置玩家经验
        
        Args:
            player(string): 玩家名称
            amount(number): 经验数量
            operation(string): set或add
            unit(string): points或levels
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await game_tools.set_experience(player, amount, operation, unit)
    
    @filter.llm_tool(name="list_players")
    async def tool_list_players(self, event: AstrMessageEvent) -> str:
        """获取在线玩家列表（无需权限）"""
        return await server_tools.list_players()
    
    @filter.llm_tool(name="say_message")
    async def tool_say_message(self, event: AstrMessageEvent, message: str) -> str:
        """向服务器广播消息
        
        Args:
            message(string): 要广播的消息
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await server_tools.say_message(message)
    
    @filter.llm_tool(name="tellraw")
    async def tool_tellraw(self, event: AstrMessageEvent, message: str, sender: str = "Bot", color: str = "yellow", target: str = "@a") -> str:
        """通过tellraw在游戏公屏发送聊天消息
        
        Args:
            message(string): 要发送的消息内容
            sender(string): 发送者名称，默认为"Bot"
            color(string): 消息颜色，可选值：yellow/red/green/blue/white/gold/aqua/dark_red等，默认为yellow
            target(string): 目标玩家，默认@a（所有玩家）
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await server_tools.tellraw(message, sender, color, target)
    
    @filter.llm_tool(name="title")
    async def tool_title(self, event: AstrMessageEvent, title_text: str, subtitle_text: str = "", color: str = "white", target: str = "@a", fade_in: int = 10, stay: int = 70, fade_out: int = 20) -> str:
        """在玩家屏幕中央显示标题
        
        Args:
            title_text(string): 标题文本
            subtitle_text(string): 副标题文本，可选
            color(string): 标题颜色，可选值：yellow/red/green/blue/white/gold/aqua/dark_red等，默认为white
            target(string): 目标玩家，默认@a（所有玩家）
            fade_in(number): 淡入时间（tick），默认10
            stay(number): 停留时间（tick），默认70
            fade_out(number): 淡出时间（tick），默认20
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await server_tools.title(title_text, subtitle_text, color, target, fade_in, stay, fade_out)
    
    @filter.llm_tool(name="save_world")
    async def tool_save_world(self, event: AstrMessageEvent) -> str:
        """保存世界数据"""
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await server_tools.save_world()
    
    @filter.llm_tool(name="whitelist_list")
    async def tool_whitelist_list(self, event: AstrMessageEvent) -> str:
        """获取白名单列表（无需权限）"""
        return await server_tools.whitelist_list()
    
    @filter.llm_tool(name="banlist")
    async def tool_banlist(self, event: AstrMessageEvent, ban_type: str = "players") -> str:
        """获取封禁列表（无需权限）
        
        Args:
            ban_type(string): players或ips
        """
        return await server_tools.banlist(ban_type)
    
    @filter.llm_tool(name="execute_command")
    async def tool_execute_command(self, event: AstrMessageEvent, command: str) -> str:
        """执行自定义MC命令
        
        Args:
            command(string): 要执行的命令（不需要/前缀）
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await server_tools.execute_command(command)
    
    @filter.llm_tool(name="set_weather")
    async def tool_set_weather(self, event: AstrMessageEvent, weather_type: str, duration: int = None) -> str:
        """设置天气
        
        Args:
            weather_type(string): clear/rain/thunder
            duration(number): 可选，持续时间（秒）
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await world_tools.set_weather(weather_type, duration)
    
    @filter.llm_tool(name="set_time")
    async def tool_set_time(self, event: AstrMessageEvent, time_value: str) -> str:
        """设置时间
        
        Args:
            time_value(string): 时间值，如day/noon/night/midnight或具体数字
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await world_tools.set_time(time_value)
    
    @filter.llm_tool(name="set_difficulty")
    async def tool_set_difficulty(self, event: AstrMessageEvent, difficulty: str) -> str:
        """设置难度
        
        Args:
            difficulty(string): peaceful/easy/normal/hard
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await world_tools.set_difficulty(difficulty)
    
    @filter.llm_tool(name="set_gamerule")
    async def tool_set_gamerule(self, event: AstrMessageEvent, rule: str, value: str) -> str:
        """设置游戏规则
        
        Args:
            rule(string): 游戏规则名称
            value(string): 规则值（true/false）
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await world_tools.set_gamerule(rule, value)
    
    @filter.llm_tool(name="summon_entity")
    async def tool_summon_entity(self, event: AstrMessageEvent, entity: str, x: float = None, y: float = None, z: float = None) -> str:
        """生成实体
        
        Args:
            entity(string): 实体类型
            x(number): X坐标
            y(number): Y坐标
            z(number): Z坐标
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await world_tools.summon_entity(entity, x, y, z)
    
    @filter.llm_tool(name="execute_script")
    async def tool_execute_script(self, event: AstrMessageEvent, script: str, timeout: int = 60) -> str:
        """执行Python脚本来完成复杂的MC管理任务
        
        此工具允许你编写简单的Python脚本，调用现有的MC管理工具函数来完成复杂任务。
        脚本中可以使用所有已注册的工具函数，如kick_player、give_item、set_weather等。
        脚本会异步执行，适合需要多步操作或循环的任务。
        
        示例脚本：
        ```python
        # 给所有在线玩家发送欢迎消息和钻石
        import asyncio
        
        async def main():
            # 获取在线玩家
            players_result = await list_players()
            print(f"在线玩家: {players_result}")
            
            # 给每个玩家发送消息和物品
            await tellraw("欢迎来到服务器！", sender="系统", color="gold")
            await give_item("@a", "diamond", 5)
            print("已给所有玩家5个钻石")
        ```
        
        Args:
            script(string): 要执行的Python脚本代码
            timeout(number): 超时时间（秒），默认60秒
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        
        try:
            result = await self.script_executor.execute_script(script, timeout=timeout)
            
            if result["success"]:
                output = result["output"] if result["output"] else "脚本执行成功（无输出）"
                return f"✓ 脚本执行成功\n\n输出:\n{output}"
            else:
                return f"✗ 脚本执行失败\n\n错误:\n{result['error']}\n\n输出:\n{result['output']}"
                
        except Exception as e:
            logger.error(f"执行脚本时出错: {e}")
            return f"✗ 脚本执行异常: {str(e)}"
    
    @filter.llm_tool(name="list_script_tools")
    async def tool_list_script_tools(self, event: AstrMessageEvent) -> str:
        """列出脚本中可以使用的所有工具函数（无需权限）
        
        返回所有已注册到脚本执行器的工具函数列表及其说明。
        这些工具可以在execute_script中直接调用。
        """
        tools_info = self.script_executor.get_available_tools()
        
        result = "📋 脚本可用工具列表:\n\n"
        
        # 按类别分组
        categories = {
            "玩家管理": ["kick_player", "ban_player", "pardon_player", "op_player", "deop_player",
                       "whitelist_add", "whitelist_remove"],
            "游戏操作": ["give_item", "teleport_player", "set_gamemode", "kill_entity",
                       "clear_inventory", "set_experience"],
            "服务器管理": ["list_players", "say_message", "tellraw", "title", "save_world",
                        "whitelist_list", "banlist", "execute_command"],
            "世界管理": ["set_weather", "set_time", "set_difficulty", "set_gamerule", "summon_entity"]
        }
        
        for category, tool_names in categories.items():
            result += f"【{category}】\n"
            for tool_name in tool_names:
                if tool_name in tools_info:
                    doc = tools_info[tool_name].split('\n')[0]  # 只取第一行
                    result += f"  • {tool_name}: {doc}\n"
            result += "\n"
        
        result += f"总计: {len(tools_info)} 个工具函数\n"
        result += "\n使用示例:\n"
        result += "await give_item('@a', 'diamond', 10)  # 给所有玩家10个钻石\n"
        result += "await set_weather('clear')  # 设置晴天"
        
        return result
    
    @filter.llm_tool(name="send_to_qq_group")
    async def tool_send_to_qq_group(self, event: AstrMessageEvent, message: str) -> str:
        """向绑定的QQ群发送消息
        
        当MC玩家发送消息触发LLM时，LLM的回复默认只会在MC中显示。
        使用此工具可以将消息同时发送到绑定的QQ群，让QQ群成员也能看到。
        
        Args:
            message(string): 要发送到QQ群的消息内容
        """
        # 检查是否启用了统一上下文
        if not self.enable_unified_context:
            return "❌ 未启用统一上下文功能(enable_unified_context)，无法发送到QQ群"
        
        # 检查是否配置了UMO
        if not self.unified_group_umo:
            return "❌ 未配置统一上下文UMO(unified_group_umo)，无法发送到QQ群"
        
        try:
            from astrbot.api.event import MessageChain
            
            # 构造消息链
            message_chain = MessageChain().message(message)
            
            # 使用配置的UMO字符串直接发送
            await self.context.send_message(self.unified_group_umo, message_chain)
            
            return f"✓ 已发送到QQ群"
            
        except Exception as e:
            logger.error(f"发送消息到QQ群失败: {e}")
            return f"❌ 发送到QQ群失败: {str(e)}"

    # 工具已通过 @filter.llm_tool 装饰器自动注册到AstrBot
    # 用户直接与LLM对话时，LLM会自动识别并调用这些MC管理工具
    # 无需命令前缀，直接说"查看在线玩家"、"踢出Steve"等即可
    
    @filter.command("test_connection")
    async def test_connection(self, event: AstrMessageEvent):
        '''测试MC服务器RCON连接状态'''
        logger.info("触发test_connection指令，正在测试RCON连接...")
        
        try:
            success, message = await self.rcon.test_connection_async()
            if success:
                result = f"✓ RCON连接成功\n服务器: {self.config.get('rcon_host')}:{self.config.get('rcon_port')}\n{message}"
                logger.info(f"RCON连接测试成功: {message}")
            else:
                result = f"✗ RCON连接失败\n服务器: {self.config.get('rcon_host')}:{self.config.get('rcon_port')}\n原因: {message}"
                logger.warning(f"RCON连接测试失败: {message}")
        except Exception as e:
            result = f"✗ RCON连接测试出错\n错误: {str(e)}"
            logger.error(f"RCON连接测试出错: {str(e)}")
        
        yield event.plain_result(result)

    @filter.command("test_log")
    async def cmd_test_log_connection(self, event: AstrMessageEvent):
        """测试与日志服务器的连接并读取最新一条日志"""
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            yield event.plain_result(error_msg)
            return
        
        if not self.log_client:
            yield event.plain_result("日志监控功能未启用")
            return
        
        try:
            success, log_content = await self.log_client.test_connection()
            yield event.plain_result(log_content)
        except Exception as e:
            yield event.plain_result(f"错误: {e}")
