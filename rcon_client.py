"""
Minecraft RCON客户端封装
支持Fabric、Forge、NeoForge等所有使用标准RCON协议的服务器
"""

from mcrcon import MCRcon
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MinecraftRCON:
    """Minecraft RCON客户端封装类"""
    
    def __init__(self, host: str, port: int, password: str):
        """
        初始化RCON客户端
        
        Args:
            host: MC服务器地址
            port: RCON端口（默认25575）
            password: RCON密码
        """
        self.host = host
        self.port = port
        self.password = password
        self._connected = False
    
    def execute(self, command: str) -> str:
        """
        执行RCON命令
        
        Args:
            command: 要执行的MC命令（不需要/前缀）
            
        Returns:
            命令执行结果
        """
        # 移除可能的/前缀
        if command.startswith('/'):
            command = command[1:]
        
        try:
            with MCRcon(self.host, self.password, port=self.port) as mcr:
                response = mcr.command(command)
                logger.info(f"执行命令: {command}, 响应: {response}")
                return response if response else "命令执行成功（无返回信息）"
        except ConnectionRefusedError:
            error_msg = f"无法连接到服务器 {self.host}:{self.port}，请检查服务器是否启动且RCON已启用"
            logger.error(error_msg)
            return f"错误: {error_msg}"
        except Exception as e:
            error_msg = f"执行命令时出错: {str(e)}"
            logger.error(error_msg)
            return f"错误: {error_msg}"
    
    def test_connection(self) -> tuple[bool, str]:
        """
        测试RCON连接
        
        Returns:
            (是否成功, 消息)
        """
        try:
            with MCRcon(self.host, self.password, port=self.port) as mcr:
                response = mcr.command("list")
                return True, f"连接成功！{response}"
        except ConnectionRefusedError:
            return False, f"无法连接到 {self.host}:{self.port}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def get_online_players(self) -> tuple[int, list[str]]:
        """
        获取在线玩家列表
        
        Returns:
            (在线人数, 玩家列表)
        """
        response = self.execute("list")
        
        # 解析响应，格式通常为: "There are X of a max of Y players online: player1, player2"
        try:
            if "There are" in response:
                # 提取玩家数量
                parts = response.split("players online:")
                count_part = parts[0]
                # 从 "There are X of a max of Y" 中提取X
                count = int(count_part.split()[2])
                
                # 提取玩家列表
                if len(parts) > 1 and parts[1].strip():
                    players = [p.strip() for p in parts[1].split(",") if p.strip()]
                else:
                    players = []
                
                return count, players
            else:
                return 0, []
        except Exception:
            return 0, []
    
    def execute_safe(self, command: str, dangerous_commands: list[str] = None) -> tuple[bool, str]:
        """
        安全执行命令（检查是否为危险命令）
        
        Args:
            command: 要执行的命令
            dangerous_commands: 危险命令列表
            
        Returns:
            (是否执行, 结果消息)
        """
        if dangerous_commands is None:
            dangerous_commands = ["stop", "ban-ip", "op", "deop"]
        
        cmd_base = command.split()[0].lower() if command else ""
        
        if cmd_base in dangerous_commands:
            return False, f"命令 '{cmd_base}' 被标记为危险命令，已阻止执行"
        
        return True, self.execute(command)