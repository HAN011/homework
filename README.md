# TCP 图像上传示例 ✅
一个简单、易读的基于 Python socket 的图像上传演示项目，包含：
- **`server.py`** — 多线程 TCP 服务器，接收客户端发送的图片并保存到指定目录。
- **`client.py`** — 从磁盘读取并发送单张图片到服务器（示例用法：PowerShell）。
- **`camera_client.py`** — 可选：多线程摄像头客户端，捕获视频帧并编码为 JPEG 后发送。
---

## 🔧 特性
- 简单的二进制传输协议（见下方 Protocol）。
- 每个客户端连接由独立线程处理（服务器端）。
- 摄像头客户端使用生产者-消费者队列和发送线程，支持丢帧策略以保持实时性。
---

## 📡 传输协议（协议细节）
传输流程（按顺序）:
1. 发送 4 字节的 filename 长度，网络字节序（struct `!I`）。
2. 发送 filename 的 UTF-8 字节（不包含终止符）。
3. 发送 8 字节的文件大小（unsigned long long，struct `!Q`，网络字节序）。
4. 发送文件二进制数据（exactly filesize 字节）。
服务器端按上述顺序读取并将接收到的数据保存为带时间戳的文件，以避免命名冲突。
---

## 🧰 环境与安装
推荐在虚拟环境中运行（PowerShell 示例）：
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

requirements 默认包含：

- `opencv-python`（仅 camera_client.py 需要）

---

## ▶️ 使用示例（PowerShell）

1) 启动服务器（在本机监听 9000 端口，并保存到 `received_images`）

```powershell
python .\server.py --host 0.0.0.0 --port 9000 --dest received_images
```

2) 发送单张图片

```powershell
python .\client.py --host 127.0.0.1 --port 9000 --file C:\path\to\image.jpg
```

3) 使用摄像头发送（索引 0，8 FPS）

```powershell
python .\camera_client.py --host 127.0.0.1 --port 9000 --cam 0 --fps 8
```

4) 在服务器端验证接收文件（PowerShell）

```powershell
Get-ChildItem -Path .\received_images -File | Select-Object Name, Length, LastWriteTime
```

---

## ✅ 快速自测（生成 1x1 PNG 并发送）

在项目目录下运行（PowerShell）：

```powershell
#$base64 是一个 1x1 PNG 的 base64 编码
$b=[System.Convert]::FromBase64String('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=')
[System.IO.File]::WriteAllBytes('test_image.png',$b)
python .\client.py --host 127.0.0.1 --port 9000 --file .\test_image.png
Get-ChildItem -Path .\received_images -File | Select-Object Name, Length
```

---

## ⚠️ 注意事项与故障排查

- 防火墙：若跨主机测试，请允许服务器端口（如 9000）的 TCP 访问。
- 文件大小：当前实现没有硬性限制，请在生产环境加入大小限制与校验（如 MD5/SHA256）。
- 连接中断：如果传输过程中连接断开，服务器端会在写文件时抛出异常并关闭连接。
- 摄像头无法打开：确认摄像头权限、索引是否正确，或使用其他摄像头软件验证设备。

---

## 🔐 可选改进（建议）

- 使用 TLS（`ssl`）保护传输通道并做双向认证。
- 添加简单身份验证或 API key（在握手阶段传递并验证）。
- 在服务器端验证图片类型（magic bytes）并限制最大尺寸。
- 支持断点续传或传输校验和以确保完整性。
- 使用 asyncio + aiofiles 或更高性能的框架以提升吞吐量。

---

## 📁 项目结构

```
./
├─ server.py           # TCP 接收服务器
├─ client.py           # 发送单张图片的客户端
├─ camera_client.py    # 多线程摄像头采集并发送
├─ requirements.txt
└─ README.md
```

---

## 📄 许可证

MIT License。


