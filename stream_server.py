import socket
import threading
import cv2
import pickle
import struct
from datetime import datetime
import os

class VideoStreamServer:
    def __init__(self, host='0.0.0.0', port=8888, save_dir='videos'):
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self.server_socket = None
        self.clients = []
        self.ensure_directory()
    
    def ensure_directory(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"  创建视频存储目录: {self.save_dir}")
    
    def handle_video_client(self, client_socket, client_addr):
        print(f"  视频客户端连接: {client_addr}")
        data = b""
        payload_size = struct.calcsize("Q")
        
        # 视频录制相关变量
        video_writer = None
        frame_width = 640  # 默认宽度
        frame_height = 480  # 默认高度
        fps = 30  # 帧率
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4编码
        is_first_frame = True
        
        try:
            while True:
                # 循环接收直到累积至少8字节数据，接收帧大小信息
                while len(data) < payload_size:
                    packet = client_socket.recv(4096)
                    # 若收到空数据，表示连接关闭
                    if not packet:
                        return
                    data += packet
                
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]
                
                # 接收帧数据
                while len(data) < msg_size:
                    data += client_socket.recv(4096)
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                # 反序列化帧
                frame = pickle.loads(frame_data)#将字节流转换回原始数据格式
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)#将内存中的图像数据解码为OpenCV图像格式
                
                if frame is not None:
                    # 如果是第一帧，初始化视频写入器
                    if is_first_frame:
                        frame_height, frame_width = frame.shape[:2]
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        video_filename = f"video_{client_addr[0]}_{timestamp}.mp4"
                        video_path = os.path.join(self.save_dir, video_filename)
                        
                        # 创建视频写入器
                        video_writer = cv2.VideoWriter(
                            video_path, 
                            fourcc, 
                            fps, 
                            (frame_width, frame_height)
                        )
                        
                        if not video_writer.isOpened():
                            print(f"  无法创建视频文件: {video_path}")
                            video_writer = None
                        else:
                            print(f"  开始录制视频: {video_filename}")
                            is_first_frame = False
                    
                    # 写入帧到视频文件
                    if video_writer is not None:
                        video_writer.write(frame)
                    
                    # 显示帧（可选）
                    cv2.imshow(f"Video from {client_addr}", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        
        except Exception as e:
            print(f"  视频流处理错误: {e}")
        finally:
            # 释放视频写入器
            if video_writer is not None:
                video_writer.release()
                print(f"  视频保存完成")
            
            client_socket.close()
            cv2.destroyAllWindows()
            print(f"  视频客户端断开: {client_addr}")
    
    def start_video_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"  视频流服务器启动在 {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, client_addr = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_video_client,
                    args=(client_socket, client_addr)
                )
                client_thread.daemon = True
                client_thread.start()
                self.clients.append((client_socket, client_thread))
                
        except KeyboardInterrupt:
            print("\n  视频服务器关闭")
        finally:
            for client_socket, _ in self.clients:
                client_socket.close()
            self.server_socket.close()

if __name__ == "__main__":
    video_server = VideoStreamServer()
    video_server.start_video_server()