"""
世界操作工具
包含天气、时间、难度、游戏规则、生成实体等功能
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..rcon_client import MinecraftRCON


# 全局RCON客户端引用
_rcon: "MinecraftRCON" = None


def set_rcon(rcon: "MinecraftRCON"):
    """设置RCON客户端"""
    global _rcon
    _rcon = rcon


def get_rcon() -> "MinecraftRCON":
    """获取RCON客户端"""
    if _rcon is None:
        raise RuntimeError("RCON客户端未初始化")
    return _rcon


# ============ 工具函数定义 ============


async def set_weather(weather_type: str, duration: Optional[int] = None) -> str:
    """
    设置游戏天气

    Args:
        weather_type(string): 天气类型，可选值：clear（晴天）、rain（雨天）、thunder（雷暴）
        duration(number): 可选，持续时间（秒），不填则使用默认时间

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 标准化天气类型
    weather_map = {
        "晴天": "clear",
        "晴": "clear",
        "雨天": "rain",
        "下雨": "rain",
        "雨": "rain",
        "雷暴": "thunder",
        "雷雨": "thunder",
        "打雷": "thunder",
    }
    weather_type = weather_map.get(weather_type, weather_type.lower())
    
    if weather_type not in ["clear", "rain", "thunder"]:
        return f"错误: 无效的天气类型 '{weather_type}'，可选值：clear、rain、thunder"
    
    if duration:
        result = await rcon.execute_async(f"weather {weather_type} {duration}")
    else:
        result = await rcon.execute_async(f"weather {weather_type}")
    
    return f"设置天气为 {weather_type}: {result}"


async def set_time(time_value: str) -> str:
    """
    设置游戏时间

    Args:
        time_value(string): 时间值，可以是数字（游戏刻）或预设值：day（白天）、noon（正午）、night（夜晚）、midnight（午夜）

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 标准化时间值
    time_map = {
        "白天": "day",
        "日出": "day",
        "正午": "noon",
        "中午": "noon",
        "夜晚": "night",
        "晚上": "night",
        "午夜": "midnight",
        "凌晨": "midnight",
        "日落": "18000",
    }
    time_value = time_map.get(time_value, time_value.lower())
    
    result = await rcon.execute_async(f"time set {time_value}")
    return f"设置时间为 {time_value}: {result}"


async def add_time(amount: int) -> str:
    """
    增加游戏时间

    Args:
        amount(number): 要增加的时间（游戏刻，20刻=1秒）

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = await rcon.execute_async(f"time add {amount}")
    return f"增加时间 {amount} 刻: {result}"


async def set_difficulty(difficulty: str) -> str:
    """
    设置游戏难度

    Args:
        difficulty(string): 难度等级，可选值：peaceful（和平）、easy（简单）、normal（普通）、hard（困难）

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 标准化难度值
    difficulty_map = {
        "和平": "peaceful",
        "简单": "easy",
        "普通": "normal",
        "困难": "hard",
        "0": "peaceful",
        "1": "easy",
        "2": "normal",
        "3": "hard",
    }
    difficulty = difficulty_map.get(difficulty, difficulty.lower())
    
    if difficulty not in ["peaceful", "easy", "normal", "hard"]:
        return f"错误: 无效的难度 '{difficulty}'，可选值：peaceful、easy、normal、hard"
    
    result = await rcon.execute_async(f"difficulty {difficulty}")
    return f"设置难度为 {difficulty}: {result}"


async def set_gamerule(rule: str, value: str) -> str:
    """
    设置游戏规则

    Args:
        rule(string): 游戏规则名称，如doDaylightCycle、keepInventory、mobGriefing等
        value(string): 规则值，通常为true或false

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 常用规则中文映射
    rule_map = {
        "昼夜更替": "doDaylightCycle",
        "保留背包": "keepInventory",
        "死亡不掉落": "keepInventory",
        "生物破坏": "mobGriefing",
        "怪物破坏": "mobGriefing",
        "自然生命恢复": "naturalRegeneration",
        "火焰蔓延": "doFireTick",
        "天气变化": "doWeatherCycle",
    }
    rule = rule_map.get(rule, rule)
    
    # 标准化布尔值
    value_map = {
        "开": "true",
        "关": "false",
        "是": "true",
        "否": "false",
        "开启": "true",
        "关闭": "false",
    }
    value = value_map.get(value, value.lower())
    
    result = await rcon.execute_async(f"gamerule {rule} {value}")
    return f"设置游戏规则 {rule} = {value}: {result}"


async def summon_entity(entity: str, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None) -> str:
    """
    在指定位置生成实体

    Args:
        entity(string): 实体类型，如zombie、creeper、pig、minecraft:iron_golem等
        x(number): 可选，X坐标，不填则在随机位置生成
        y(number): 可选，Y坐标
        z(number): 可选，Z坐标

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 确保实体ID格式正确
    if not entity.startswith("minecraft:"):
        entity = f"minecraft:{entity}"
    
    if x is not None and y is not None and z is not None:
        result = await rcon.execute_async(f"summon {entity} {x} {y} {z}")
        return f"在 ({x}, {y}, {z}) 生成 {entity}: {result}"
    else:
        result = await rcon.execute_async(f"summon {entity}")
        return f"生成 {entity}: {result}"


async def fill_blocks(x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, block: str, mode: str = "replace") -> str:
    """
    用指定方块填充区域

    Args:
        x1(number): 起点X坐标
        y1(number): 起点Y坐标
        z1(number): 起点Z坐标
        x2(number): 终点X坐标
        y2(number): 终点Y坐标
        z2(number): 终点Z坐标
        block(string): 方块类型，如stone、air、diamond_block
        mode(string): 填充模式，可选：replace（替换）、destroy（摧毁）、keep（保留）、hollow（空心）、outline（轮廓）

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 确保方块ID格式正确
    if not block.startswith("minecraft:"):
        block = f"minecraft:{block}"
    
    result = await rcon.execute_async(f"fill {x1} {y1} {z1} {x2} {y2} {z2} {block} {mode}")
    return f"填充区域 ({x1},{y1},{z1}) 到 ({x2},{y2},{z2}) 为 {block}: {result}"


async def set_spawn(x: int, y: int, z: int) -> str:
    """
    设置世界出生点

    Args:
        x(number): X坐标
        y(number): Y坐标
        z(number): Z坐标

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = await rcon.execute_async(f"setworldspawn {x} {y} {z}")
    return f"设置世界出生点为 ({x}, {y}, {z}): {result}"