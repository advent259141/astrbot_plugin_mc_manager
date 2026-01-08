# AstrBot MC服务器管理插件

通过LLM智能管理Minecraft服务器的AstrBot插件。支持Fabric、Forge、NeoForge等所有使用标准RCON协议的服务器。

## ✨ 功能特性

- 🤖 **自然语言交互**：无需命令前缀，直接与LLM对话即可管理服务器
- 🎮 **全面管理**：支持玩家管理、游戏操作、服务器管理、世界操作等功能
- 🔒 **权限控制**：支持管理员白名单，确保服务器安全
- 🌐 **跨平台兼容**：基于RCON协议，支持Fabric、Forge、NeoForge等各种服务端

## 📦 安装

### 方法一：通过AstrBot插件市场安装（推荐）

1. 打开AstrBot管理面板
2. 进入「插件管理」
3. 搜索 `mc_manager`
4. 点击安装

### 方法二：手动安装

1. 下载本插件到 AstrBot 的 `data/plugins/` 目录
2. 重启 AstrBot

## ⚙️ 配置

### 1. Minecraft服务器配置

在您的MC服务器 `server.properties` 文件中启用RCON：

```properties
enable-rcon=true
rcon.port=25575
rcon.password=your_secure_password
broadcast-rcon-to-ops=true
```

**重要**：修改后需要重启MC服务器。

### 2. 插件配置

在AstrBot管理面板中配置本插件：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `rcon_host` | MC服务器地址 | `localhost` |
| `rcon_port` | RCON端口 | `25575` |
| `rcon_password` | RCON密码 | - |
| `admin_ids` | 管理员ID列表（QQ号或MC玩家名） | `[]`（空表示所有人可用） |
| `enable_dangerous_commands` | 启用危险命令（如stop） | `false` |
| `enable_log_monitor` | 启用MC日志监控 | `false` |
| `log_server_host` | 日志服务器地址 | `127.0.0.1` |
| `log_server_port` | 日志服务器端口 | `25576` |
| `wake_words` | 唤醒词列表 | `["bot"]` |
| `enable_chat_response` | 将LLM响应发送回MC聊天框 | `true` |
| `bot_nickname` | 在MC中显示的机器人昵称 | `"Bot"` |

配置示例：
```json
{
  "rcon_host": "127.0.0.1",
  "rcon_port": 25575,
  "rcon_password": "your_password",
  "admin_ids": ["123456789", "Steve", "Alex"],
  "enable_dangerous_commands": false,
  "enable_log_monitor": true,
  "log_server_host": "127.0.0.1",
  "log_server_port": 25576,
  "wake_words": ["小助手", "bot"],
  "enable_chat_response": true,
  "bot_nickname": "MC助手"
}
```

### 3. MC游戏内聊天支持（可选）

如果启用 `enable_log_monitor`，可以在MC游戏内直接与机器人对话：

1. **在MC服务器机器上运行日志服务器**：
   ```bash
   python log_server.py /path/to/minecraft/logs/latest.log
   ```

2. **配置权限**：
   - `admin_ids` 中添加MC玩家名即可授予权限
   - 例如：`"admin_ids": ["Steve", "Alex"]` 允许这两个MC玩家执行管理命令
   - 格式：MC玩家的user_id为 `mc_player_{玩家名}`

3. **在MC中使用**：
   - 发送包含唤醒词的消息：`小助手 查看在线玩家`
   - 机器人会自动回复到MC聊天框

**权限校验说明**：
- QQ消息：使用QQ号校验（如 `"123456789"`）
- MC消息：使用玩家名校验（如 `"Steve"`）
- 系统会自动识别消息来源并应用对应的权限规则

## 📖 使用方法

**无需命令前缀！** 直接与AstrBot对话即可管理服务器。

### 使用示例

```
用户: 查看在线玩家
Bot: 在线玩家: There are 3 of a max of 20 players online: Steve, Alex, Notch

用户: 把Steve踢出服务器，原因是挂机太久
Bot: 踢出玩家 Steve: Kicked Steve: 挂机太久

用户: 给Alex 64个钻石
Bot: 给予 Alex 64个 minecraft:diamond: Given [Diamond] x 64 to Alex

用户: 把时间调成白天
Bot: 设置时间为 day: Set the time to 1000

用户: 把天气变成晴天
Bot: 设置天气为 clear: Changed the weather to clear

用户: 封禁Hacker这个玩家
Bot: 封禁玩家 Hacker: Banned Hacker: 违反服务器规则

用户: 把难度调成困难
Bot: 设置难度为 hard: Set game difficulty to Hard

用户: 开启死亡不掉落
Bot: 设置游戏规则 keepInventory = true: Gamerule keepInventory is now set to: true
```

## 🛠️ 支持的功能

### 玩家管理
- ✅ 踢出玩家（kick）
- ✅ 封禁/解封玩家（ban/pardon）
- ✅ 管理OP权限（op/deop）
- ✅ 白名单管理（whitelist）

### 游戏操作
- ✅ 给予物品（give）
- ✅ 传送玩家（tp）
- ✅ 设置游戏模式（gamemode）
- ✅ 杀死实体（kill）
- ✅ 清空背包（clear）
- ✅ 设置经验（xp）

### 服务器管理
- ✅ 查看在线玩家（list）
- ✅ 服务器广播（say）
- ✅ 保存世界（save-all）
- ✅ 查看封禁列表（banlist）
- ⚠️ 停止服务器（stop）- 需启用危险命令

### 世界操作
- ✅ 设置天气（weather）
- ✅ 设置时间（time）
- ✅ 设置难度（difficulty）
- ✅ 设置游戏规则（gamerule）
- ✅ 生成实体（summon）

## 🔐 安全建议

1. **设置强密码**：RCON密码应该使用强密码
2. **限制管理员**：在 `admin_ids` 中明确指定可以使用的QQ号
3. **禁用危险命令**：保持 `enable_dangerous_commands` 为 `false`，除非确实需要
4. **防火墙配置**：如果MC服务器和AstrBot不在同一台机器，确保RCON端口的安全

## 🔧 故障排除

### 连接失败

**如何开启RCON：**

1. **找到服务器配置文件**：在MC服务器根目录找到 `server.properties` 文件
2. **编辑配置文件**：使用文本编辑器打开，添加或修改以下配置：
   ```properties
   enable-rcon=true
   rcon.port=25575
   rcon.password=your_secure_password
   broadcast-rcon-to-ops=true
   ```
3. **设置安全密码**：将 `your_secure_password` 替换为强密码
4. **重启服务器**：保存文件后，**必须重启MC服务器**才能生效
5. **验证配置**：服务器启动后，查看日志确认 "RCON running on..." 字样

**故障排查步骤：**

1. 确认MC服务器已启动
2. 确认 `server.properties` 中已启用RCON（`enable-rcon=true`）
3. 确认端口号和密码正确
4. 确认防火墙允许RCON端口
5. 如果MC和AstrBot在不同机器，确认 `rcon_host` 设置为MC服务器的IP地址而非 `localhost`

### 命令无响应

1. 检查AstrBot是否正确配置了LLM提供者
2. 检查插件配置是否正确
3. 查看AstrBot日志获取详细错误信息

## 📝 更新日志

### v1.0.0
- 初始版本
- 支持玩家管理、游戏操作、服务器管理、世界操作
- 支持LLM智能理解自然语言（无需命令前缀）
- 支持管理员权限控制

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 💬 支持

如有问题，请在GitHub仓库提交Issue。