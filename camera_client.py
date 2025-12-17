import socket
import cv2
import threading
import time
import struct
import pickle

class CameraClient:
    def __init__(self, server_host='127.0.0.1', server_port=8888):
        # 初始化服务器地址和端口
        self.server_host = server_host
        self.server_port = server_port
        # 初始化摄像头
        self.camera = None
        # 流媒体状态标志
        self.is_streaming = False
        # 缓冲区，存储待发送视频
        self.frame_queue = []
        # 线程锁用于保护对frame_queue的并发访问
        self.queue_lock = threading.Lock()
    
    def connect_to_server(self):
        try:
            # 创建套接字并连接到服务器
            # socket.AF_INET 这个参数代表使用 IPv4 地址族。
            # socket.SOCK_STREAM 这个参数代表使用 TCP 协议。
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            print(f"  连接到视频服务器 {self.server_host}:{self.server_port}")
            return True
        # try 块中的任何一步发生了错误（例如：服务器未启动、网络不通、端口错误等），程序会立即跳转到 except 块
        except Exception as e:
            print(f"  连接失败: {e}")
            return False
    
    def start_camera(self):
        print(f"send_frames 运行在线程: {threading.get_ident()}")
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            print("  无法打开摄像头")
            return False
        print("  摄像头启动成功")
        return True
    
    def capture_frames(self):# 捕获线程
        print(f"capture_frames 运行在线程: {threading.get_ident()}")
        while self.is_streaming:
            # ret:是否成功读取帧，frame:读取到的帧
            ret, frame = self.camera.read()
            if ret:
                # 显示帧
                cv2.imshow('Camera Stream', frame)
                # 检测按键
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.is_streaming = False
                    break
                
                with self.queue_lock:# 获取线程锁，保护对frame_queue的访问
                    if len(self.frame_queue) < 10:
                        self.frame_queue.append(frame)
            time.sleep(0.03)#挂起30ms，控制帧率

    def send_frames(self):#发送线程
        while self.is_streaming:
            with self.queue_lock:
                if self.frame_queue:
                    frame = self.frame_queue.pop(0)
                    # 压缩并序列化帧
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    data = pickle.dumps(buffer)
                    # 发送帧大小和数据
                    try:
                        # 将数据长度打包为8字节无符号长整型
                        message = struct.pack("Q", len(data)) + data
                        self.client_socket.sendall(message)
                    except:
                        break
            time.sleep(0.01)
    
    def start_streaming(self):
        if not self.connect_to_server() or not self.start_camera():
            return False
        
        self.is_streaming = True
        
        # 启动捕获线程
        capture_thread = threading.Thread(target=self.capture_frames)
        # 将线程设置为守护线程
        # 守护线程的特点：当主线程结束时，守护线程会自动终止
        # 如果不设为守护线程，即使主线程结束，子线程可能继续运行，导致程序无法正常退出 
        capture_thread.daemon = True
        capture_thread.start()
        
        # 启动发送线程
        send_thread = threading.Thread(target=self.send_frames)
        send_thread.daemon = True
        send_thread.start()
        print("  开始视频流传输 (按 'q' 停止)")
        try:
            while self.is_streaming:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                time.sleep(0.1)
        # finally: 无论 try 块中是否发生异常，都会执行此代码块
        finally:
            self.stop_streaming()

    def stop_streaming(self):
        self.is_streaming = False
        if self.camera:
            self.camera.release()
        if hasattr(self, 'client_socket'):#检查对象是否有 client_socket 属性
            self.client_socket.close()
            cv2.destroyAllWindows()
        print(" ️ 视频流停止")

if __name__ == "__main__":
    camera_client = CameraClient()
    camera_client.start_streaming()