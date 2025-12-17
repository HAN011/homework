import asyncio
import cv2
import struct

# --- 配置区域 ---
SERVER_IP = '127.0.0.1'  # 服务器 IP
SERVER_PORT = 8888       # 服务器端口
CAMERA_INDEX = 0         # 摄像头索引 (0, 1, 2...)

async def send_video():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    # 可选：降低分辨率以提高传输流畅度
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print(f"无法打开摄像头 (Index: {CAMERA_INDEX})")
        return

    try:
        print(f"正在连接 TCP 服务器 {SERVER_IP}:{SERVER_PORT} ...")
        # 建立 TCP 连接
        reader, writer = await asyncio.open_connection(SERVER_IP, SERVER_PORT)
        print("连接成功，开始传输视频流...")

        header_struct = struct.Struct("Q")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("摄像头读取失败")
                break

            # 1. 图片压缩 (JPEG)
            # 原始数据量太大(640*480*3字节)，必须压缩后传输
            # 质量参数 80 (0-100)，越低数据越小但画质越差
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            result, img_encode = cv2.imencode('.jpg', frame, encode_param)
            
            if not result:
                continue
            
            # 获取字节流
            data = img_encode.tobytes()
            
            # 2. 封装 TCP 数据包
            # 协议格式: [8字节长度] + [JPEG数据]
            header = header_struct.pack(len(data))
            
            # 3. 发送数据
            writer.write(header + data)
            
            # 4. 刷新缓冲区，确保数据真正发送到 Socket
            await writer.drain()
            
            # 控制采集帧率 (约30fps)，避免占用过多 CPU
            await asyncio.sleep(0.03)

    except ConnectionRefusedError:
        print("错误: 无法连接服务器，请检查服务器是否启动。")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        cap.release()
        if 'writer' in locals():
            writer.close()
            await writer.wait_closed()
        print("客户端已关闭")

if __name__ == '__main__':
    try:
        # Windows 兼容性
        import sys
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(send_video())
    except KeyboardInterrupt:
        pass