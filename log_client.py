"""
Minecraft日志客户端
连接到日志服务器，接收日志并解析玩家聊天消息
支持心跳机制检测服务端断连
"""

import asyncio
import json
import time
import re
from typing import Optional, Callable, List
from astrbot.api import logger


class LogClient:
    """日志接收客户端（支持心跳机制）"""
    
    # Minecraft聊天日志的正则表达式模式
    # 只提取玩家名和消息内容
    CHAT_PATTERN = re.compile(
        r'<(?P<player>[^>]+)>\s+(?P<message>.*)'
    )
    
    # 玩家登入事件正则
    JOIN_PATTERN = re.compile(
        r'\[Server thread/INFO\]: (\S+) joined the game$'
    )
    
    # 玩家登出事件正则
    LEAVE_PATTERN = re.compile(
        r'\[Server thread/INFO\]: (\S+) left the game$'
    )
    
    # 达成成就事件正则
    ADVANCEMENT_PATTERN = re.compile(
        r'\[Server thread/INFO\]: (\S+) has made the advancement \[(.+)\]$'
    )
    
    # 死亡事件关键词列表
    DEATH_KEYWORDS = [
        "was slain by",       # 被杀 (玩家/僵尸)
        "was shot by",        # 被射杀 (骷髅)
        "fell from",          # 摔死
        "drowned",            # 淹死
        "suffocated in",      # 窒息/卡墙
        "tried to swim in",   # 岩浆
        "was blown up by",    # 苦力怕/TNT
        "hit the ground",     # 摔死(着陆过猛)
        "withered away",      # 凋零
        "went up in flames",  # 烧死
        "burned to death",    # 烧死
        "was killed",         # 被杀
        "was pummeled by",    # 被打死
        "starved to death",   # 饿死
        "was pricked to death", # 被仙人掌扎死
        "was impaled",        # 被三叉戟刺死
        "experienced kinetic energy", # 动能伤害(鞘翅)
        "blew up",            # 爆炸
        "was squashed",       # 被压扁
        "fell out of",        # 掉出世界
        "died",               # 通用死亡
    ]
    
    # 心跳配置
    HEARTBEAT_TIMEOUT = 30  # 心跳超时时间（秒），超过此时间未收到服务端心跳则认为断连
    
    def __init__(self, host: str = "127.0.0.1", port: int = 25576,
                 reconnect_interval: int = 10, max_reconnect_attempts: int = 0):
        """
        初始化日志客户端
        
        Args:
            host: 服务器地址
            port: 服务器端口
            reconnect_interval: 重连间隔（秒），0表示不自动重连
            max_reconnect_attempts: 最大重连次数，0表示无限重试
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.running = False
        self.on_chat_message: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None  # 断连回调
        self.on_reconnect: Optional[Callable] = None  # 重连成功回调
        self.on_player_join: Optional[Callable] = None  # 玩家登入回调
        self.on_player_leave: Optional[Callable] = None  # 玩家登出回调
        self.on_player_advancement: Optional[Callable] = None  # 玩家成就回调
        self.on_player_death: Optional[Callable] = None  # 玩家死亡回调
        self.original_event = None  # 存储原始事件，用于伪造事件
        self.fake_event_handler: Optional[Callable] = None  # 伪造事件处理器
        self.last_heartbeat_time = 0  # 最后收到心跳的时间
        
        # 重连配置
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_count = 0
        self.should_reconnect = True  # 是否应该继续重连
    
    async def connect(self):
        """连接到日志服务器"""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0
            )
            self.running = True
            logger.info(f"已连接到日志服务器: {self.host}:{self.port}")
            
            # 重置重连计数
            if self.reconnect_count > 0:
                logger.info(f"重连成功（共尝试 {self.reconnect_count} 次）")
                self.reconnect_count = 0
                
                # 调用重连成功回调
                if self.on_reconnect:
                    try:
                        await self.on_reconnect()
                    except Exception as e:
                        logger.error(f"执行重连回调时出错: {e}")
            
            return True
        except asyncio.TimeoutError:
            logger.error(f"连接日志服务器超时: {self.host}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"连接日志服务器失败: {e}")
            return False
    
    async def disconnect(self, stop_reconnect: bool = True):
        """
        断开连接
        
        Args:
            stop_reconnect: 是否停止自动重连
        """
        self.running = False
        if stop_reconnect:
            self.should_reconnect = False
        
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
        
        self.reader = None
        self.writer = None
        logger.info("已断开与日志服务器的连接")
    
    async def start_listening(self):
        """开始监听日志消息（支持心跳检测和自动重连）"""
        self.should_reconnect = True
        self.reconnect_count = 0
        
        while self.should_reconnect:
            # 如果未连接，尝试连接
            if not self.reader:
                if not await self.connect():
                    # 连接失败，检查是否需要重连
                    if self.reconnect_interval > 0 and self._should_retry_reconnect():
                        self.reconnect_count += 1
                        logger.info(f"将在 {self.reconnect_interval} 秒后重连（第 {self.reconnect_count} 次尝试）")
                        await asyncio.sleep(self.reconnect_interval)
                        continue
                    else:
                        logger.error("连接失败且不再重试")
                        break
            
            logger.info("开始监听日志消息...")
            
            # 启动心跳检测任务
            heartbeat_task = asyncio.create_task(self._check_heartbeat())
            
            try:
                while self.running:
                    # 读取一行数据
                    try:
                        line = await asyncio.wait_for(self.reader.readline(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # 超时继续循环
                        continue
                    
                    if not line:
                        logger.warning("服务器连接断开")
                        break
                    
                    # 解码并处理消息
                    try:
                        msg_str = line.decode('utf-8').strip()
                        if msg_str:
                            await self._process_message(msg_str)
                    except Exception as e:
                        logger.error(f"处理消息时出错: {e}")
                        
            except Exception as e:
                logger.error(f"监听日志时出错: {e}")
            finally:
                heartbeat_task.cancel()
                await self.disconnect(stop_reconnect=False)
                
                # 调用断连回调
                if self.on_disconnect:
                    try:
                        await self.on_disconnect()
                    except Exception as e:
                        logger.error(f"执行断连回调时出错: {e}")
            
            # 检查是否需要重连
            if self.should_reconnect and self.reconnect_interval > 0 and self._should_retry_reconnect():
                self.reconnect_count += 1
                logger.info(f"将在 {self.reconnect_interval} 秒后重连（第 {self.reconnect_count} 次尝试）")
                await asyncio.sleep(self.reconnect_interval)
            else:
                break
        
        logger.info("日志监听已停止")
    
    def _should_retry_reconnect(self) -> bool:
        """
        检查是否应该继续重连
        
        Returns:
            是否应该继续重连
        """
        if self.max_reconnect_attempts == 0:
            # 无限重试
            return True
        return self.reconnect_count < self.max_reconnect_attempts
    
    async def _process_message(self, msg_str: str):
        """
        处理服务端消息（JSON格式）
        
        Args:
            msg_str: JSON消息字符串
        """
        try:
            msg = json.loads(msg_str)
            msg_type = msg.get('type')
            
            if msg_type == 'ping':
                # 收到心跳包，更新时间并响应
                self.last_heartbeat_time = time.time()
                await self._send_pong()
                
            elif msg_type == 'log':
                # 收到日志消息，处理日志内容
                log_content = msg.get('content', '')
                if log_content:
                    self._process_log_line(log_content)
                    
        except json.JSONDecodeError as e:
            logger.error(f"收到非JSON格式的消息，已忽略: {msg_str[:100]}... 错误: {e}")
    
    async def _send_pong(self):
        """发送心跳响应"""
        if self.writer:
            try:
                pong = json.dumps({'type': 'pong', 'timestamp': time.time()}) + '\n'
                self.writer.write(pong.encode('utf-8'))
                await self.writer.drain()
            except Exception as e:
                logger.error(f"发送心跳响应失败: {e}")
    
    async def _check_heartbeat(self):
        """检查心跳超时"""
        self.last_heartbeat_time = time.time()
        
        while self.running:
            await asyncio.sleep(5)  # 每5秒检查一次
            
            if time.time() - self.last_heartbeat_time > self.HEARTBEAT_TIMEOUT:
                logger.error(f"服务端心跳超时（超过{self.HEARTBEAT_TIMEOUT}秒），断开连接")
                self.running = False
                break
    
    def _process_log_line(self, log_line: str):
        """
        处理日志行，提取各种游戏事件
        
        Args:
            log_line: 日志行内容
        """
        # 1. 检查玩家登入事件
        match_join = self.JOIN_PATTERN.search(log_line)
        if match_join:
            player = match_join.group(1)
            logger.info(f"[MC事件] {player} 加入了游戏")
            if self.on_player_join:
                try:
                    asyncio.create_task(self.on_player_join(player))
                except Exception as e:
                    logger.error(f"处理玩家登入回调时出错: {e}")
            return
        
        # 2. 检查玩家登出事件
        match_leave = self.LEAVE_PATTERN.search(log_line)
        if match_leave:
            player = match_leave.group(1)
            logger.info(f"[MC事件] {player} 离开了游戏")
            if self.on_player_leave:
                try:
                    asyncio.create_task(self.on_player_leave(player))
                except Exception as e:
                    logger.error(f"处理玩家登出回调时出错: {e}")
            return
        
        # 3. 检查达成成就事件
        match_adv = self.ADVANCEMENT_PATTERN.search(log_line)
        if match_adv:
            player = match_adv.group(1)
            advancement = match_adv.group(2)
            logger.info(f"[MC事件] {player} 达成了成就 [{advancement}]")
            if self.on_player_advancement:
                try:
                    asyncio.create_task(self.on_player_advancement(player, advancement))
                except Exception as e:
                    logger.error(f"处理成就回调时出错: {e}")
            return
        
        # 4. 检查死亡事件
        death_info = self._parse_death_event(log_line)
        if death_info:
            player, reason = death_info
            logger.info(f"[MC事件] {player} 死亡: {reason}")
            if self.on_player_death:
                try:
                    asyncio.create_task(self.on_player_death(player, reason))
                except Exception as e:
                    logger.error(f"处理死亡回调时出错: {e}")
            return
        
        # 5. 检查玩家聊天消息
        match = self.CHAT_PATTERN.search(log_line)
        if match:
            player = match.group('player')
            message = match.group('message')
            
            logger.info(f"[MC聊天] <{player}> {message}")
            
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
    
    def _parse_death_event(self, log_line: str) -> Optional[tuple[str, str]]:
        """
        解析死亡事件
        
        Args:
            log_line: 日志行内容
            
        Returns:
            (玩家名, 死因) 或 None
        """
        # 必须包含 [Server thread/INFO]:
        if "[Server thread/INFO]:" not in log_line:
            return None
        
        try:
            # 提取日志内容部分
            content = log_line.split("[Server thread/INFO]: ")[1].strip()
            
            # 排除玩家聊天 (聊天信息以 <玩家名> 开头)
            if content.startswith("<"):
                return None
            
            # 排除其他系统信息
            if any(keyword in content for keyword in ["logged in", "lost connection", "joined the game", "left the game"]):
                return None
            
            # 检查是否包含死亡关键词
            for keyword in self.DEATH_KEYWORDS:
                if keyword in content:
                    # 提取玩家名（通常是句子第一个词）
                    parts = content.split(" ")
                    if parts:
                        player_name = parts[0]
                        return (player_name, content)
            
            return None
        except Exception:
            return None
    
    def set_chat_callback(self, callback: Callable):
        """
        设置聊天消息回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback(player: str, message: str, time: str)
        """
        self.on_chat_message = callback
    
    def set_disconnect_callback(self, callback: Callable):
        """
        设置断连回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback()
        """
        self.on_disconnect = callback
    
    def set_reconnect_callback(self, callback: Callable):
        """
        设置重连成功回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback()
        """
        self.on_reconnect = callback
    
    def set_player_join_callback(self, callback: Callable):
        """
        设置玩家登入回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback(player: str)
        """
        self.on_player_join = callback
    
    def set_player_leave_callback(self, callback: Callable):
        """
        设置玩家登出回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback(player: str)
        """
        self.on_player_leave = callback
    
    def set_player_advancement_callback(self, callback: Callable):
        """
        设置玩家达成成就回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback(player: str, advancement: str)
        """
        self.on_player_advancement = callback
    
    def set_player_death_callback(self, callback: Callable):
        """
        设置玩家死亡回调函数
        
        Args:
            callback: 回调函数，签名为 async def callback(player: str, reason: str)
        """
        self.on_player_death = callback
    
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
