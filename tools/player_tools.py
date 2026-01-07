"""
玩家管理工具
包含踢出、封禁、解封、OP权限、白名单等功能
"""

from typing import TYPE_CHECKING

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


def kick_player(player: str, reason: str = "被管理员踢出") -> str:
    """
    踢出指定玩家

    Args:
        player(string): 要踢出的玩家名称
        reason(string): 踢出原因，默认为"被管理员踢出"

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"kick {player} {reason}")
    return f"踢出玩家 {player}: {result}"


def ban_player(player: str, reason: str = "违反服务器规则") -> str:
    """
    封禁指定玩家

    Args:
        player(string): 要封禁的玩家名称
        reason(string): 封禁原因，默认为"违反服务器规则"

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"ban {player} {reason}")
    return f"封禁玩家 {player}: {result}"


def pardon_player(player: str) -> str:
    """
    解封指定玩家

    Args:
        player(string): 要解封的玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"pardon {player}")
    return f"解封玩家 {player}: {result}"


def op_player(player: str) -> str:
    """
    给予玩家OP权限

    Args:
        player(string): 要给予OP权限的玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"op {player}")
    return f"给予 {player} OP权限: {result}"


def deop_player(player: str) -> str:
    """
    移除玩家的OP权限

    Args:
        player(string): 要移除OP权限的玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"deop {player}")
    return f"移除 {player} 的OP权限: {result}"


def whitelist_add(player: str) -> str:
    """
    将玩家添加到白名单

    Args:
        player(string): 要添加到白名单的玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"whitelist add {player}")
    return f"添加 {player} 到白名单: {result}"


def whitelist_remove(player: str) -> str:
    """
    将玩家从白名单移除

    Args:
        player(string): 要从白名单移除的玩家名称

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"whitelist remove {player}")
    return f"从白名单移除 {player}: {result}"