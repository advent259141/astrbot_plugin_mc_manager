"""
脚本执行器模块
允许LLM编写和异步执行简单的Python脚本，调用现有的MC管理工具
"""

import asyncio
import traceback
from typing import Dict, Any, Callable, Optional
from astrbot.api import logger


class ScriptExecutor:
    """脚本执行器，用于执行LLM生成的Python脚本"""
    
    def __init__(self):
        """初始化脚本执行器"""
        self.tools: Dict[str, Callable] = {}
        self.running_scripts: Dict[str, asyncio.Task] = {}
        self._script_counter = 0
    
    def register_tool(self, name: str, func: Callable):
        """
        注册工具函数供脚本调用
        
        Args:
            name: 工具函数名称
            func: 工具函数对象
        """
        self.tools[name] = func
        logger.debug(f"脚本执行器已注册工具: {name}")
    
    def register_tools(self, tools: Dict[str, Callable]):
        """
        批量注册工具函数
        
        Args:
            tools: 工具函数字典 {name: func}
        """
        for name, func in tools.items():
            self.register_tool(name, func)
    
    async def execute_script(
        self, 
        script: str, 
        script_id: Optional[str] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        异步执行Python脚本
        
        Args:
            script: 要执行的Python脚本代码
            script_id: 脚本ID，不提供则自动生成
            timeout: 超时时间（秒），默认60秒
            
        Returns:
            执行结果字典:
            {
                "success": bool,
                "script_id": str,
                "output": str,  # 正常输出
                "error": str,   # 错误信息
                "status": str   # "completed", "timeout", "error"
            }
        """
        if script_id is None:
            self._script_counter += 1
            script_id = f"script_{self._script_counter}"
        
        logger.info(f"开始执行脚本 [{script_id}]")
        
        # 创建执行任务
        task = asyncio.create_task(
            self._run_script(script, script_id)
        )
        self.running_scripts[script_id] = task
        
        try:
            # 等待任务完成或超时
            result = await asyncio.wait_for(task, timeout=timeout)
            result["status"] = "completed"
            logger.info(f"脚本 [{script_id}] 执行完成")
            return result
            
        except asyncio.TimeoutError:
            task.cancel()
            logger.warning(f"脚本 [{script_id}] 执行超时")
            return {
                "success": False,
                "script_id": script_id,
                "output": "",
                "error": f"脚本执行超时（{timeout}秒）",
                "status": "timeout"
            }
        finally:
            # 清理任务
            if script_id in self.running_scripts:
                del self.running_scripts[script_id]
    
    async def _run_script(self, script: str, script_id: str) -> Dict[str, Any]:
        """
        实际执行脚本的内部方法
        
        Args:
            script: Python脚本代码
            script_id: 脚本ID
            
        Returns:
            执行结果字典
        """
        output_lines = []
        error_msg = ""
        
        # 创建执行上下文
        context = {
            "__builtins__": __builtins__,
            "asyncio": asyncio,
            "logger": logger,
            # 添加所有注册的工具
            **self.tools
        }
        
        # 添加print函数重定向
        def custom_print(*args, **kwargs):
            """自定义print函数，捕获输出"""
            line = " ".join(str(arg) for arg in args)
            output_lines.append(line)
            logger.debug(f"[{script_id}] {line}")
        
        context["print"] = custom_print
        
        try:
            # 编译脚本
            compiled_code = compile(script, f"<script_{script_id}>", "exec")
            
            # 执行脚本
            exec(compiled_code, context)
            
            # 如果脚本中定义了main函数，执行它
            if "main" in context and callable(context["main"]):
                result = context["main"]()
                # 如果main是async函数
                if asyncio.iscoroutine(result):
                    await result
            
            return {
                "success": True,
                "script_id": script_id,
                "output": "\n".join(output_lines),
                "error": ""
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"脚本 [{script_id}] 执行失败: {error_msg}")
            
            return {
                "success": False,
                "script_id": script_id,
                "output": "\n".join(output_lines),
                "error": error_msg
            }
    
    def get_running_scripts(self) -> list:
        """
        获取当前正在运行的脚本列表
        
        Returns:
            脚本ID列表
        """
        return list(self.running_scripts.keys())
    
    async def cancel_script(self, script_id: str) -> bool:
        """
        取消正在执行的脚本
        
        Args:
            script_id: 脚本ID
            
        Returns:
            是否成功取消
        """
        if script_id in self.running_scripts:
            task = self.running_scripts[script_id]
            task.cancel()
            del self.running_scripts[script_id]
            logger.info(f"已取消脚本 [{script_id}]")
            return True
        return False
    
    def get_available_tools(self) -> Dict[str, str]:
        """
        获取所有可用工具的列表及其文档
        
        Returns:
            工具名称到文档字符串的映射
        """
        tools_info = {}
        for name, func in self.tools.items():
            doc = func.__doc__ or "无文档"
            tools_info[name] = doc.strip()
        return tools_info