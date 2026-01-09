"""
Minecraft日志客户端
连接到日志服务器，接收日志并解析玩家聊天消息
"""

import asyncio
import re
from typing import Optional, Callable, List
from astrbot.api import logger


class LogClient:
    """日志接收客户端"""
    
    # Minecraft聊天日志的正则表达式模式
    # 只提取玩家名和消息内容
    CHAT_PATTERN = re.compile(
        r'<(?P<player>[^>]+)>\s+(?P<message>.*)'
    )
    
    def __init__(self, host: str = "127.0.0.1", port: int = 25576):
        """
        初始化日志客户端
        
        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.running = False
        self.on_chat_message: Optional[Callable] = None
        self.original_event = None  # 存储原始事件，用于伪造事件
        self.fake_event_handler: Optional[Callable] = None  # 伪造事件处理器
    
    async def connect(self):
        """连接到日志服务器"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.running = True
            logger.info(f"已连接到日志服务器: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接日志服务器失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        logger.info("已断开与日志服务器的连接")
    
    async def start_listening(self):
        """开始监听日志消息"""
        if not self.reader:
            logger.error("未连接到服务器")
            return
        logger.info("开始监听日志消息...")
        
        try:
            while self.running:
                # 读取一行数据
                line = await self.reader.readline()
                if not line:
                    logger.warning("服务器连接断开")
                    break
                
                # 解码并处理日志行
                log_line = line.decode('utf-8').strip()
                if log_line:
                    self._process_log_line(log_line)
                    
        except Exception as e:
            logger.error(f"监听日志时出错: {e}")
        finally:
            await self.disconnect()
    
    def _process_log_line(self, log_line: str):
        """
        处理日志行，提取玩家聊天消息
        
        Args:
            log_line: 日志行内容
        """
        # 尝试匹配聊天消息格式
        match = self.CHAT_PATTERN.search(log_line)
        if match:
            player = match.group('player')
            message = match.group('message')
            
            logger.info(f"[MC] <{player}> {message}")
            
            # 提交所有MC消息到AstrBot，由框架的wake_prefix控制是否调用LLM
            if self.fake_event_handler:
                try:
                    # 传入玩家名和消息
                    asyncio.create_task(
                        self.fake_event_handler(player, message)
                    )
                except Exception as e:
                    logger.error(f"提交MC消息时出错: {e}")
            
            # 如果设置了回调函数，调用它
            if self.on_chat_message:
                try:
                    asyncio.create_task(
                        self.on_chat_message(player, message, "")  # 时间留空
                    )
                except Exception as e:
                    logger.error(f"处理聊天消息回调时出错: {e}")
    
    def set_chat_callback(self, callback: Callable):
        """
        设置聊天消息回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback(player: str, message: str, time: str)
        """
        self.on_chat_message = callback
    
    def set_original_event(self, event):
        """
        设置原始事件，用于伪造事件时提供上下文
        
        Args:
            event: AstrMessageEvent 原始消息事件
        """
        self.original_event = event
    
    def set_fake_event_handler(self, handler: Callable):
        """
        设置伪造事件处理器
        
        Args:
            handler: 处理器函数，签名为 async def handler(message_text: str)
        """
        self.fake_event_handler = handler
    
    async def test_connection(self):
        """
        测试与服务端的连接并读取最新一条日志
        
        Returns:
            (是否成功, 日志内容或错误信息)
        """
        try:
            # 创建临时连接
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            
            # 尝试读取一条日志（设置10秒超时）
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=10.0)
                if line:
                    log_content = line.decode('utf-8').strip()
                    writer.close()
                    await writer.wait_closed()
                    return True, log_content
                else:
                    writer.close()
                    await writer.wait_closed()
                    return True, "未接收到日志数据"
            except asyncio.TimeoutError:
                writer.close()
                await writer.wait_closed()
                return True, "10秒内未收到新日志"
            
        except asyncio.TimeoutError:
            return False, "连接超时"
        except ConnectionRefusedError:
            return False, "连接被拒绝，日志服务器未运行"
        except Exception as e:
            return False, f"连接失败: {e}"


async def example_chat_handler(player: str, message: str, time: str):
    """示例聊天消息处理函数"""
    logger.info(f"收到聊天消息 - 时间:{time}, 玩家:{player}, 内容:{message}")
    
    # 这里可以添加更多处理逻辑
    # 例如：关键词回复、命令处理等


async def main():
    """示例：独立运行日志客户端"""
    import sys
    
    client = LogClient()
    
    # 检查是否是测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试连接
        await client.test_connection()
        return
    
    # 设置聊天消息处理回调
    client.set_chat_callback(example_chat_handler)
    
    # 连接并开始监听
    if await client.connect():
        try:
            await client.start_listening()
        except KeyboardInterrupt:
            await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
