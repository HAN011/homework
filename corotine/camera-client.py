import socket
import cv2
import struct
import time

# 配置
SERVER_IP = '127.0.0.1'
SERVER_PORT = 8888
CAMERA_INDEX = 0

def start_client():
    # 创建原生 TCP Socket
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    cap = cv2.VideoCapture(CAMERA_INDEX)
    header_struct = struct.Struct("Q")

    try:
        print(f"连接服务器 {SERVER_IP}...")
        client_sock.connect((SERVER_IP, SERVER_PORT))
        print("连接成功！")

        while True:
            ret, frame = cap.read()
            if not ret: break

            # 图片压缩
            _, img_encode = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            data = img_encode.tobytes()

            # 封装包头并使用 socket.sendall 发送
            # sendall 内部会自动循环调用 send 直到所有数据发完
            header = header_struct.pack(len(data))
            client_sock.sendall(header + data)

            # 控制频率
            time.sleep(0.03)

    except Exception as e:
        print(f"错误: {e}")
    finally:
        cap.release()
        client_sock.close()

if __name__ == '__main__':
    start_client()