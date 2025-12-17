import asyncio
import cv2
import struct
import numpy as np
import os
import datetime

# --- 配置区域 ---
HOST = '0.0.0.0'  # 监听所有网卡
PORT = 8888       # 监听端口
SAVE_DIR = "camera_records"  # 视频保存路径

# 确保保存目录存在
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

async def handle_client(reader, writer):
    """
    协程处理函数：处理单个 TCP 连接的生命周期
    reader: asyncio.StreamReader (封装了 TCP Socket 的接收)
    writer: asyncio.StreamWriter (封装了 TCP Socket 的发送)
    """
    # 获取客户端 Socket 地址 (IP, Port)
    addr = writer.get_extra_info('peername')
    client_id = f"Cam_{addr[0]}_{addr[1]}"
    print(f"[+] 摄像头接入: {client_id}")

    # 定义包头格式：Q 代表 unsigned long long (8字节)，用于存放图片大小
    header_struct = struct.Struct("Q")
    payload_size = header_struct.size
    
    video_writer = None

    try:
        while True:
            # --- TCP 接收阶段 (解决粘包问题) ---
            
            # 1. 先读头部 (8字节)，获知接下来的图片有多大
            try:
                # readexactly 对应 socket 的 recv，但在读满指定字节前不会返回
                header_data = await reader.readexactly(payload_size)
            except asyncio.IncompleteReadError:
                # 客户端断开连接
                break

            # 解析头部，得到图片数据的长度
            msg_size = header_struct.unpack(header_data)[0]

            # 2. 再读数据体 (根据头部指定的长度读取图片数据)
            try:
                frame_data = await reader.readexactly(msg_size)
            except asyncio.IncompleteReadError:
                break

            # --- 数据处理阶段 ---
            
            # 解码图片 (将字节流转为 OpenCV 图像)
            np_arr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                # --- 存储逻辑 ---
                # 如果是该连接的第一帧，初始化视频写入器
                if video_writer is None:
                    height, width = frame.shape[:2]
                    # 生成唯一文件名: 路径/客户端ID_时间.mp4
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(SAVE_DIR, f"{client_id}_{timestamp}.mp4")
                    
                    # 初始化 VideoWriter ('mp4v' 编码通常兼容性较好)
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    video_writer = cv2.VideoWriter(filename, fourcc, 25.0, (width, height))
                    print(f"[*] 开始录制 {client_id} -> {filename}")

                # 写入视频文件
                video_writer.write(frame)

                # --- 显示逻辑 ---
                cv2.imshow(client_id, frame)
                
                # 处理按键 (仅为了响应窗口事件，实际退出逻辑在主循环)
                if cv2.waitKey(1) & 0xFF == 27: # ESC 键
                    break
            
            # --- 协程调度 ---
            # 这一步至关重要，让出控制权，使服务器能同时处理其他摄像头的 Socket 数据
            await asyncio.sleep(0)

    except ConnectionResetError:
        print(f"[-] 连接重置: {client_id}")
    except Exception as e:
        print(f"[-] 异常 {client_id}: {e}")
    finally:
        # --- 资源释放 ---
        print(f"[-] 断开连接: {client_id}")
        if video_writer:
            video_writer.release()
            print(f"[*] 录像已保存: {client_id}")
            
        writer.close()
        await writer.wait_closed()
        try:
            cv2.destroyWindow(client_id)
        except:
            pass

async def main():
    # 启动 TCP 服务器，绑定回调函数 handle_client
    server = await asyncio.start_server(handle_client, HOST, PORT)
    
    # 获取服务器 Socket 信息
    addr = server.sockets[0].getsockname()
    print(f"==========================================")
    print(f" TCP 监控服务器启动成功")
    print(f" 监听地址: {addr}")
    print(f" 存储路径: {os.path.abspath(SAVE_DIR)}")
    print(f" 等待摄像头连接 (支持多路同时接入)...")
    print(f"==========================================")

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        # Windows 环境下的 EventLoop 策略兼容性设置
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已停止")