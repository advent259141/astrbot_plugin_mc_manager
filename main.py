"""
AstrBot MC服务器管理插件
通过LLM智能管理Minecraft服务器，支持Fabric/Forge/NeoForge
"""

import asyncio
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api import AstrBotConfig, logger

from .rcon_client import MinecraftRCON
from .tools import player_tools, game_tools, server_tools, world_tools


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
        
        # 注入RCON客户端到所有工具模块
        self._inject_rcon()
        
        logger.info(f"MC Manager插件已加载，RCON: {self.config.get('rcon_host')}:{self.config.get('rcon_port')}")
        
        # 测试RCON连接并记录状态
        self._test_and_log_connection()
    
    def _test_and_log_connection(self):
        """测试RCON连接并记录连接状态到日志"""
        try:
            success, message = self.rcon.test_connection()
            if success:
                logger.info(f"✓ RCON连接成功: {self.config.get('rcon_host')}:{self.config.get('rcon_port')} - {message}")
            else:
                logger.warning(f"✗ RCON连接失败: {self.config.get('rcon_host')}:{self.config.get('rcon_port')} - {message}")
        except Exception as e:
            logger.error(f"✗ RCON连接测试出错: {str(e)}")
    
    def _inject_rcon(self):
        """将RCON客户端注入到所有工具模块"""
        player_tools.set_rcon(self.rcon)
        game_tools.set_rcon(self.rcon)
        server_tools.set_rcon(self.rcon)
        server_tools.set_dangerous_commands_enabled(self.enable_dangerous)
        world_tools.set_rcon(self.rcon)
    
    def is_admin(self, user_id: str) -> bool:
        """
        检查用户是否为管理员
        
        Args:
            user_id: 用户ID（QQ号）
            
        Returns:
            是否为管理员，如果admin_ids为空则所有人都是管理员
        """
        if not self.admin_ids:
            return True
        return str(user_id) in self.admin_ids
    
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
        return await asyncio.to_thread(player_tools.kick_player, player, reason)
    
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
        return await asyncio.to_thread(player_tools.ban_player, player, reason)
    
    @filter.llm_tool(name="pardon_player")
    async def tool_pardon_player(self, event: AstrMessageEvent, player: str) -> str:
        """解封指定玩家
        
        Args:
            player(string): 要解封的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(player_tools.pardon_player, player)
    
    @filter.llm_tool(name="op_player")
    async def tool_op_player(self, event: AstrMessageEvent, player: str) -> str:
        """给予玩家OP权限
        
        Args:
            player(string): 要给予OP权限的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(player_tools.op_player, player)
    
    @filter.llm_tool(name="deop_player")
    async def tool_deop_player(self, event: AstrMessageEvent, player: str) -> str:
        """移除玩家的OP权限
        
        Args:
            player(string): 要移除OP权限的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(player_tools.deop_player, player)
    
    @filter.llm_tool(name="whitelist_add")
    async def tool_whitelist_add(self, event: AstrMessageEvent, player: str) -> str:
        """将玩家添加到白名单
        
        Args:
            player(string): 要添加到白名单的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(player_tools.whitelist_add, player)
    
    @filter.llm_tool(name="whitelist_remove")
    async def tool_whitelist_remove(self, event: AstrMessageEvent, player: str) -> str:
        """将玩家从白名单移除
        
        Args:
            player(string): 要从白名单移除的玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(player_tools.whitelist_remove, player)
    
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
        return await asyncio.to_thread(game_tools.give_item, player, item, count)
    
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
        return await asyncio.to_thread(game_tools.teleport_player, player, target)
    
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
        return await asyncio.to_thread(game_tools.set_gamemode, player, mode)
    
    @filter.llm_tool(name="kill_entity")
    async def tool_kill_entity(self, event: AstrMessageEvent, target: str) -> str:
        """杀死指定实体
        
        Args:
            target(string): 目标选择器或玩家名称
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(game_tools.kill_entity, target)
    
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
        return await asyncio.to_thread(game_tools.clear_inventory, player, item)
    
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
        return await asyncio.to_thread(game_tools.set_experience, player, amount, operation, unit)
    
    @filter.llm_tool(name="list_players")
    async def tool_list_players(self, event: AstrMessageEvent) -> str:
        """获取在线玩家列表"""
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(server_tools.list_players)
    
    @filter.llm_tool(name="say_message")
    async def tool_say_message(self, event: AstrMessageEvent, message: str) -> str:
        """向服务器广播消息
        
        Args:
            message(string): 要广播的消息
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(server_tools.say_message, message)
    
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
        return await asyncio.to_thread(server_tools.tellraw, message, sender, color, target)
    
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
        return await asyncio.to_thread(server_tools.title, title_text, subtitle_text, color, target, fade_in, stay, fade_out)
    
    @filter.llm_tool(name="save_world")
    async def tool_save_world(self, event: AstrMessageEvent) -> str:
        """保存世界数据"""
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(server_tools.save_world)
    
    @filter.llm_tool(name="whitelist_list")
    async def tool_whitelist_list(self, event: AstrMessageEvent) -> str:
        """获取白名单列表"""
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(server_tools.whitelist_list)
    
    @filter.llm_tool(name="banlist")
    async def tool_banlist(self, event: AstrMessageEvent, ban_type: str = "players") -> str:
        """获取封禁列表
        
        Args:
            ban_type(string): players或ips
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(server_tools.banlist, ban_type)
    
    @filter.llm_tool(name="execute_command")
    async def tool_execute_command(self, event: AstrMessageEvent, command: str) -> str:
        """执行自定义MC命令
        
        Args:
            command(string): 要执行的命令（不需要/前缀）
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(server_tools.execute_command, command)
    
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
        return await asyncio.to_thread(world_tools.set_weather, weather_type, duration)
    
    @filter.llm_tool(name="set_time")
    async def tool_set_time(self, event: AstrMessageEvent, time_value: str) -> str:
        """设置时间
        
        Args:
            time_value(string): 时间值，如day/noon/night/midnight或具体数字
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(world_tools.set_time, time_value)
    
    @filter.llm_tool(name="set_difficulty")
    async def tool_set_difficulty(self, event: AstrMessageEvent, difficulty: str) -> str:
        """设置难度
        
        Args:
            difficulty(string): peaceful/easy/normal/hard
        """
        has_permission, error_msg = self._check_permission(event)
        if not has_permission:
            return error_msg
        return await asyncio.to_thread(world_tools.set_difficulty, difficulty)
    
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
        return await asyncio.to_thread(world_tools.set_gamerule, rule, value)
    
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
        return await asyncio.to_thread(world_tools.summon_entity, entity, x, y, z)

    # 工具已通过 @filter.llm_tool 装饰器自动注册到AstrBot
    # 用户直接与LLM对话时，LLM会自动识别并调用这些MC管理工具
    # 无需命令前缀，直接说"查看在线玩家"、"踢出Steve"等即可
    
    @filter.command("test_connection")
    async def test_connection(self, event: AstrMessageEvent):
        '''测试MC服务器RCON连接状态'''
        logger.info("触发test_connection指令，正在测试RCON连接...")
        
        try:
            success, message = self.rcon.test_connection()
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