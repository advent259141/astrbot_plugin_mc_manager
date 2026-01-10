"""
Minecraft日志服务端
实时读取MC服务器日志文件，并通过Socket发送给客户端
支持心跳机制检测客户端断连
"""

import asyncio
import os
import json
import time
from pathlib import Path
from typing import Optional, Set, Tuple


# ============ 配置区域 ============
# 服务器监听地址
# - "127.0.0.1": 仅本地访问
# - "0.0.0.0": 允许远程访问
SERVER_HOST = "127.0.0.1"

# 服务器监听端口
SERVER_PORT = 25571

# MC服务器日志文件路径（可在这里配置，也可通过命令行参数指定）
# 示例: r"C:\minecraft_server\logs\latest.log"
# 留空则必须通过命令行参数指定
DEFAULT_LOG_PATH = r"C:\Users\Administrator\Desktop\nfwc\logs\latest.log"

# 心跳配置
HEARTBEAT_INTERVAL = 10  # 服务端发送心跳间隔（秒）
CLIENT_TIMEOUT = 30      # 客户端超时时间（秒）
# ==================================


class LogServer:
    """日志读取服务端（支持心跳机制）"""
    
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
        self.clients: Set[Tuple[asyncio.StreamReader, asyncio.StreamWriter, float]] = set()
        self.running = False
        
    async def start(self):
        """启动日志服务器"""
        if not self.log_file_path.exists():
            print(f"[ERROR] 日志文件不存在: {self.log_file_path}")
            return
        
        self.running = True
        self.server = await asyncio.start_server(
            self._handle_client, 
            self.host, 
            self.port
        )
        
        print(f"[INFO] 日志服务器已启动: {self.host}:{self.port}")
        print(f"[INFO] 监控日志文件: {self.log_file_path}")
        
        # 启动日志读取任务和心跳任务
        asyncio.create_task(self._tail_log_file())
        asyncio.create_task(self._heartbeat_task())
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """停止日志服务器"""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print("[INFO] 日志服务器已停止")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理客户端连接（支持心跳响应）"""
        addr = writer.get_extra_info('peername')
        print(f"[INFO] 客户端已连接: {addr}")
        
        # 记录客户端信息（reader, writer, 最后活跃时间）
        client_info = (reader, writer, time.time())
        self.clients.add(client_info)
        
        try:
            # 接收客户端消息（主要是心跳响应）
            while self.running:
                try:
                    # 设置读取超时
                    data = await asyncio.wait_for(reader.readline(), timeout=1.0)
                    if not data:
                        print(f"[WARNING] 客户端断开连接: {addr}")
                        break
                    
                    # 解析消息
                    try:
                        msg = json.loads(data.decode('utf-8').strip())
                        if msg.get('type') == 'pong':
                            # 更新客户端最后活跃时间
                            self.clients.discard(client_info)
                            client_info = (reader, writer, time.time())
                            self.clients.add(client_info)
                    except json.JSONDecodeError:
                        pass  # 忽略非JSON消息
                        
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue
                    
        except Exception as e:
            print(f"[ERROR] 客户端连接错误 {addr}: {e}")
        finally:
            self.clients.discard(client_info)
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            print(f"[INFO] 客户端已断开: {addr}")
    
    async def _tail_log_file(self):
        """实时读取日志文件最后一行，支持文件轮转"""
        import os
        
        current_inode = None
        current_size = 0
        file_handle = None
        check_counter = 0
        check_interval = 100  # 每100次读取检查一次文件状态（约10秒）
        
        try:
            while self.running:
                # 定期检查文件状态（而不是每次循环都检查）
                should_check = check_counter % check_interval == 0
                
                if should_check or file_handle is None:
                    # 检查文件是否存在
                    if not self.log_file_path.exists():
                        if file_handle:
                            file_handle.close()
                            file_handle = None
                        print(f"[WARNING] 日志文件不存在，等待文件创建: {self.log_file_path}")
                        await asyncio.sleep(1)
                        check_counter = 0
                        continue
                    
                    # 获取文件状态
                    try:
                        stat_info = os.stat(self.log_file_path)
                        file_inode = stat_info.st_ino
                        file_size = stat_info.st_size
                    except Exception as e:
                        print(f"[ERROR] 获取文件状态失败: {e}")
                        await asyncio.sleep(1)
                        check_counter = 0
                        continue
                    
                    # 检测文件是否被替换（inode变化）或被截断（大小变小）
                    if current_inode is None or file_inode != current_inode or file_size < current_size:
                        if file_handle:
                            file_handle.close()
                            print(f"[INFO] 检测到日志文件更新，重新打开文件")
                        
                        # 重新打开文件
                        try:
                            file_handle = open(self.log_file_path, 'r', encoding='utf-8', errors='ignore')
                            file_handle.seek(0, 2)  # 移动到文件末尾
                            current_inode = file_inode
                            current_size = file_handle.tell()
                            print(f"[INFO] 已打开新日志文件，inode={current_inode}")
                        except Exception as e:
                            print(f"[ERROR] 打开日志文件失败: {e}")
                            await asyncio.sleep(1)
                            check_counter = 0
                            continue
                
                # 读取新内容
                if file_handle:
                    try:
                        line = file_handle.readline()
                        if line:
                            current_size = file_handle.tell()
                            # 发送新行到所有客户端
                            await self._broadcast(line.strip())
                            check_counter += 1
                        else:
                            # 没有新内容，等待一下
                            await asyncio.sleep(0.1)
                            check_counter += 1
                    except Exception as e:
                        print(f"[ERROR] 读取日志文件失败: {e}")
                        # 出错时关闭文件句柄，下次循环重新打开
                        if file_handle:
                            file_handle.close()
                            file_handle = None
                        current_inode = None
                        check_counter = 0
                        await asyncio.sleep(1)
        finally:
            # 清理资源
            if file_handle:
                file_handle.close()
    
    async def _heartbeat_task(self):
        """心跳任务：定期发送心跳包并检查客户端超时"""
        while self.running:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            
            current_time = time.time()
            disconnected = set()
            
            # 发送心跳包并检查超时
            for reader, writer, last_active in list(self.clients):
                # 检查是否超时
                if current_time - last_active > CLIENT_TIMEOUT:
                    print(f"[WARNING] 客户端超时，断开连接: {writer.get_extra_info('peername')}")
                    disconnected.add((reader, writer, last_active))
                    continue
                
                # 发送心跳包
                try:
                    heartbeat = json.dumps({'type': 'ping', 'timestamp': current_time}) + '\n'
                    writer.write(heartbeat.encode('utf-8'))
                    await writer.drain()
                except Exception as e:
                    print(f"[ERROR] 发送心跳失败: {e}")
                    disconnected.add((reader, writer, last_active))
            
            # 移除断开的客户端
            for client in disconnected:
                self.clients.discard(client)
                try:
                    client[1].close()
                    await client[1].wait_closed()
                except:
                    pass
    
    async def _broadcast(self, message: str):
        """广播日志消息给所有客户端"""
        if not self.clients:
            return
        
        # 准备发送的数据（JSON格式）
        log_msg = json.dumps({'type': 'log', 'content': message}) + '\n'
        data = log_msg.encode('utf-8')
        
        # 发送给所有客户端
        disconnected = set()
        for reader, writer, last_active in list(self.clients):
            try:
                writer.write(data)
                await writer.drain()
            except Exception as e:
                print(f"[ERROR] 发送日志失败: {e}")
                disconnected.add((reader, writer, last_active))
        
        # 移除断开的客户端
        for client in disconnected:
            self.clients.discard(client)
            try:
                client[1].close()
                await client[1].wait_closed()
            except:
                pass


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