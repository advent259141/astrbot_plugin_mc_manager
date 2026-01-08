"""
Minecraft日志服务端
实时读取MC服务器日志文件，并通过Socket发送给客户端
"""

import asyncio
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


def log(msg):
    """输出日志信息"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ============ 配置区域 ============
# 服务器监听地址
# - "127.0.0.1": 仅本地访问
# - "0.0.0.0": 允许远程访问
SERVER_HOST = "127.0.0.1"

# 服务器监听端口
SERVER_PORT = 25576

# MC服务器日志文件路径（可在这里配置，也可通过命令行参数指定）
# 示例: r"C:\minecraft_server\logs\latest.log"
# 留空则必须通过命令行参数指定
DEFAULT_LOG_PATH = ""
# ==================================


class LogServer:
    """日志读取服务端"""
    
    def __init__(self, log_file_path: str, host: str = "127.0.0.1", port: int = 25576):
        """
        初始化日志服务端
        
        Args:
            log_file_path: MC服务器日志文件路径（例如：logs/latest.log）
            host: 监听地址
            port: 监听端口
        """
        self.log_file_path = Path(log_file_path)
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.clients = set()
        self.running = False
        
    async def start(self):
        """启动日志服务器"""
        if not self.log_file_path.exists():
            log(f"错误：日志文件不存在: {self.log_file_path}")
            return
        
        self.running = True
        self.server = await asyncio.start_server(
            self._handle_client, 
            self.host, 
            self.port
        )
        
        log(f"日志服务器已启动: {self.host}:{self.port}")
        log(f"监控日志文件: {self.log_file_path}")
        
        # 启动日志读取任务
        asyncio.create_task(self._tail_log_file())
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """停止日志服务器"""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        log("日志服务器已停止")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接"""
        addr = writer.get_extra_info('peername')
        log(f"客户端已连接: {addr}")
        
        client_info = (reader, writer)
        self.clients.add(client_info)
        
        try:
            # 保持连接，等待客户端断开
            while True:
                data = await reader.read(100)
                if not data:
                    break
                await asyncio.sleep(0.1)
        except Exception as e:
            log(f"错误：客户端连接错误: {e}")
        finally:
            self.clients.remove(client_info)
            writer.close()
            await writer.wait_closed()
            log(f"客户端已断开: {addr}")
    
    async def _tail_log_file(self):
        """实时读取日志文件最后一行"""
        # 移动到文件末尾
        with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)  # 移动到文件末尾
            
            while self.running:
                line = f.readline()
                if line:
                    # 发送新行到所有客户端
                    await self._broadcast(line.strip())
                else:
                    # 没有新内容，等待一下
                    await asyncio.sleep(0.1)
    
    async def _broadcast(self, message: str):
        """广播消息给所有客户端"""
        if not self.clients:
            return
        
        # 准备发送的数据（添加换行符作为分隔）
        data = (message + '\n').encode('utf-8')
        
        # 发送给所有客户端
        disconnected = set()
        for reader, writer in self.clients:
            try:
                writer.write(data)
                await writer.drain()
            except Exception as e:
                log(f"错误：发送数据失败: {e}")
                disconnected.add((reader, writer))
        
        # 移除断开的客户端
        for client in disconnected:
            self.clients.remove(client)


async def main():
    """示例：独立运行日志服务器"""
    import sys
    
    # 确定日志文件路径
    if len(sys.argv) >= 2:
        log_path = sys.argv[1]
    elif DEFAULT_LOG_PATH:
        log_path = DEFAULT_LOG_PATH
        print(f"使用配置的日志路径: {log_path}")
    else:
        print("错误：未指定日志文件路径")
        print("用法: python log_server.py <日志文件路径>")
        print("示例: python log_server.py C:/minecraft/logs/latest.log")
        print("或在代码顶部配置 DEFAULT_LOG_PATH")
        return
    
    # 创建服务器实例（使用配置的地址和端口）
    server = LogServer(log_path, host=SERVER_HOST, port=SERVER_PORT)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
