"""
游戏操作工具
包含给予物品、传送、游戏模式、经验等功能
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..rcon_client import MinecraftRCON


# 全局RCON客户端引用，由main.py注入
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


def give_item(player: str, item: str, count: int = 1) -> str:
    """
    给予玩家物品

    Args:
        player(string): 要给予物品的玩家名称，使用@p表示最近的玩家，@a表示所有玩家
        item(string): 物品ID，例如diamond、iron_sword、minecraft:golden_apple
        count(number): 物品数量，默认为1，最大64

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    # 确保物品ID格式正确
    if not item.startswith("minecraft:"):
        item = f"minecraft:{item}"
    
    # 限制数量范围
    count = max(1, min(count, 64))
    
    result = rcon.execute(f"give {player} {item} {count}")
    return f"给予 {player} {count}个 {item}: {result}"


def teleport_player(player: str, target: str) -> str:
    """
    传送玩家到目标位置或其他玩家

    Args:
        player(string): 要传送的玩家名称
        target(string): 目标位置（x y z坐标，如"100 64 200"）或目标玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"tp {player} {target}")
    return f"传送 {player} 到 {target}: {result}"


def set_gamemode(player: str, mode: str) -> str:
    """
    设置玩家的游戏模式

    Args:
        player(string): 要设置游戏模式的玩家名称
        mode(string): 游戏模式，可选值：survival（生存）、creative（创造）、adventure（冒险）、spectator（旁观）

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 标准化游戏模式名称
    mode_map = {
        "生存": "survival",
        "创造": "creative", 
        "冒险": "adventure",
        "旁观": "spectator",
        "0": "survival",
        "1": "creative",
        "2": "adventure",
        "3": "spectator",
    }
    mode = mode_map.get(mode.lower(), mode.lower())
    
    result = rcon.execute(f"gamemode {mode} {player}")
    return f"设置 {player} 的游戏模式为 {mode}: {result}"


def kill_entity(target: str) -> str:
    """
    杀死指定实体或玩家

    Args:
        target(string): 目标选择器或玩家名称，如@e[type=zombie]杀死所有僵尸，或玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"kill {target}")
    return f"杀死 {target}: {result}"


def clear_inventory(player: str, item: Optional[str] = None) -> str:
    """
    清空玩家背包或移除特定物品

    Args:
        player(string): 玩家名称
        item(string): 可选，要移除的特定物品ID，不填则清空整个背包

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    if item:
        if not item.startswith("minecraft:"):
            item = f"minecraft:{item}"
        result = rcon.execute(f"clear {player} {item}")
        return f"从 {player} 的背包移除 {item}: {result}"
    else:
        result = rcon.execute(f"clear {player}")
        return f"清空 {player} 的背包: {result}"


def set_experience(player: str, amount: int, operation: str = "set", unit: str = "points") -> str:
    """
    设置或修改玩家经验

    Args:
        player(string): 玩家名称
        amount(number): 经验数量
        operation(string): 操作类型，set（设置）或add（添加），默认为set
        unit(string): 单位，points（经验点数）或levels（等级），默认为points

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    
    # 验证操作类型
    if operation.lower() not in ["set", "add"]:
        operation = "set"
    
    # 验证单位
    if unit.lower() not in ["points", "levels"]:
        unit = "points"
    
    result = rcon.execute(f"xp {operation} {player} {amount} {unit}")
    return f"{operation} {player} 的经验 {amount} {unit}: {result}"