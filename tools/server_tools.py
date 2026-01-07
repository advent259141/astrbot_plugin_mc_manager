"""
服务器管理工具
包含查看玩家、广播消息、保存世界、停止服务器等功能
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..rcon_client import MinecraftRCON


# 全局RCON客户端引用和配置
_rcon: "MinecraftRCON" = None
_enable_dangerous_commands: bool = False


def set_rcon(rcon: "MinecraftRCON"):
    """设置RCON客户端"""
    global _rcon
    _rcon = rcon


def set_dangerous_commands_enabled(enabled: bool):
    """设置是否允许危险命令"""
    global _enable_dangerous_commands
    _enable_dangerous_commands = enabled


def get_rcon() -> "MinecraftRCON":
    """获取RCON客户端"""
    if _rcon is None:
        raise RuntimeError("RCON客户端未初始化")
    return _rcon


# ============ 工具函数定义 ============


def list_players() -> str:
    """
    获取当前在线玩家列表

    Returns:
        在线玩家信息
    """
    rcon = get_rcon()
    result = rcon.execute("list")
    return f"在线玩家: {result}"


def say_message(message: str) -> str:
    """
    向服务器所有玩家广播消息

    Args:
        message(string): 要广播的消息内容

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute(f"say {message}")
    return f"已广播消息: {message}"


def stop_server() -> str:
    """
    停止Minecraft服务器（危险操作）

    Returns:
        执行结果信息
    """
    global _enable_dangerous_commands
    
    if not _enable_dangerous_commands:
        return "错误: 停止服务器是危险操作，已被配置禁用。请在插件配置中启用 'enable_dangerous_commands' 选项。"
    
    rcon = get_rcon()
    result = rcon.execute("stop")
    return f"服务器停止命令已发送: {result}"


def save_world() -> str:
    """
    保存世界数据

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute("save-all")
    return f"世界保存: {result}"


def whitelist_list() -> str:
    """
    获取白名单列表

    Returns:
        白名单信息
    """
    rcon = get_rcon()
    result = rcon.execute("whitelist list")
    return f"白名单: {result}"


def banlist(ban_type: str = "players") -> str:
    """
    获取封禁列表

    Args:
        ban_type(string): 封禁类型，players（玩家）或ips（IP地址），默认为players

    Returns:
        封禁列表信息
    """
    rcon = get_rcon()
    
    if ban_type.lower() == "ips":
        result = rcon.execute("banlist ips")
        return f"IP封禁列表: {result}"
    else:
        result = rcon.execute("banlist players")
        return f"玩家封禁列表: {result}"


def execute_command(command: str) -> str:
    """
    执行自定义Minecraft命令（高级功能）

    Args:
        command(string): 要执行的Minecraft命令（不需要/前缀）

    Returns:
        命令执行结果
    """
    rcon = get_rcon()
    
    # 检查危险命令
    dangerous_commands = ["stop", "ban-ip"]
    cmd_base = command.split()[0].lower() if command else ""
    
    if cmd_base in dangerous_commands and not _enable_dangerous_commands:
        return f"错误: 命令 '{cmd_base}' 是危险命令，已被禁用。"
    
    result = rcon.execute(command)
    return f"执行命令 '{command}': {result}"


def get_server_status() -> str:
    """
    获取服务器状态信息

    Returns:
        服务器状态信息
    """
    rcon = get_rcon()
    
    # 获取玩家列表
    players_result = rcon.execute("list")
    
    # 尝试获取TPS（如果服务器支持）
    # 注意：这个命令在不同服务器上可能不可用
    
    return f"服务器状态:\n在线玩家: {players_result}"


def whitelist_on() -> str:
    """
    开启白名单

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute("whitelist on")
    return f"白名单已开启: {result}"


def whitelist_off() -> str:
    """
    关闭白名单

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute("whitelist off")
    return f"白名单已关闭: {result}"


def reload_whitelist() -> str:
    """
    重新加载白名单

    Returns:
        执行结果信息
    """
    rcon = get_rcon()
    result = rcon.execute("whitelist reload")
    return f"白名单已重新加载: {result}"