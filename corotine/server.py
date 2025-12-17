import socket
import asyncio
import cv2
import struct
import numpy as np
import os
import datetime

# 配置
HOST = '0.0.0.0'
PORT = 8888
SAVE_DIR = "socket_records"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

async def recv_all(loop, sock, n):
    """
    使用原生 socket.recv 的异步辅助函数：
    确保从非阻塞 socket 中读满 n 个字节。
    """
    data = b''
    while len(data) < n:
        # 使用 loop.sock_recv 代替直接的 sock.recv
        packet = await loop.sock_recv(sock, n - len(data))
        if not packet:
            return None
        data += packet
    return data

async def handle_client(sock, addr):
    """处理单个 Socket 客户端的视频流和存储"""
    loop = asyncio.get_event_loop()
    client_id = f"Cam_{addr[0]}_{addr[1]}"
    print(f"[+] 建立连接: {client_id}")

    header_struct = struct.Struct("Q")
    header_size = header_struct.size
    video_writer = None

    try:
        while True:
            # 1. 接收 8 字节头部 (socket.recv 逻辑)
            header_data = await recv_all(loop, sock, header_size)
            if not header_data: break

            msg_size = header_struct.unpack(header_data)[0]

            # 2. 接收图片数据体
            frame_data = await recv_all(loop, sock, msg_size)
            if not frame_data: break

            # 3. 解码与存储
            np_arr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is not None:
                if video_writer is None:
                    h, w = frame.shape[:2]
                    ts = datetime.datetime.now().strftime("%H%M%S")
                    filename = os.path.join(SAVE_DIR, f"{client_id}_{ts}.mp4")
                    video_writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), 25.0, (w, h))
                    print(f"[*] 录制中: {filename}")

                video_writer.write(frame)
                cv2.imshow(client_id, frame)
                if cv2.waitKey(1) & 0xFF == 27: break
            
            await asyncio.sleep(0) # 协程切片

    except Exception as e:
        print(f"[-] 异常 {client_id}: {e}")
    finally:
        print(f"[-] 释放资源: {client_id}")
        if video_writer: video_writer.release()
        sock.close()
        cv2.destroyWindow(client_id)

async def main():
    loop = asyncio.get_event_loop()

    # 创建原始 TCP Socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    server_sock.setblocking(False) # 必须设为非阻塞以配合协程

    print(f"[*] Socket Server 启动于 {HOST}:{PORT}")

    while True:
        # 异步等待新的 socket.accept
        client_sock, addr = await loop.sock_accept(server_sock)
        # 为每个新连接创建一个协程任务
        loop.create_task(handle_client(client_sock, addr))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server Stop")