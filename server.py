import socket
import os
import threading
from datetime import datetime

class ImageServer:
    def __init__(self, host='0.0.0.0', port=8888, save_dir='received_images'):
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self.server_socket = None
        self.ensure_directory()
    
    def ensure_directory(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"  创建存储目录: {self.save_dir}")
    
    def generate_filename(self, original_name):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(original_name)
        return f"{name}_{timestamp}{ext}"
    def handle_client(self, client_socket, client_addr):
        try:
            # 1. 接收固定长度的头部（4字节），表示文件信息长度
            header = client_socket.recv(4)
            if len(header) < 4:
                raise ValueError("Header too short")
            info_len = int.from_bytes(header, byteorder='big')

            # 2. 接收指定长度的文件信息
            file_info = client_socket.recv(info_len).decode('utf-8')
            filename, file_size = file_info.split(':')
            file_size = int(file_size)

            # 3. 接收文件数据（二进制）
            save_path = os.path.join(self.save_dir, self.generate_filename  (filename))
            with open(save_path, 'wb') as f:
                remaining = file_size
                while remaining > 0:
                    chunk = client_socket.recv(min(4096, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            client_socket.send("SUCCESS".encode('utf-8'))
            print(f"  文件保存成功: {save_path}")
        except Exception as e:
            print(f"  处理客户端错误: {e}")
            client_socket.send("ERROR".encode('utf-8'))
        finally:
            client_socket.close()

    # def handle_client(self, client_socket, client_addr):
    #     print(f"  客户端连接: {client_addr}")
        
    #     try:
    #         # 接收文件信息（文件名:文件大小）
    #         file_info = client_socket.recv(1024).decode('utf-8')
    #         filename, file_size = file_info.split(':')
    #         file_size = int(file_size)
    #         print(f"  接收文件: {filename}, 大小: {file_size}字节")
    #         # 生成保存路径
    #         save_filename = self.generate_filename(filename)
    #         save_path = os.path.join(self.save_dir, save_filename)
    #         # 接收文件数据
    #         received_size = 0
    #         with open(save_path, 'wb') as f:
    #             while received_size < file_size:
    #                 chunk = client_socket.recv(4096)
    #                 if not chunk:
    #                     break
    #                 f.write(chunk)
    #                 received_size += len(chunk)
    #         # 发送确认
    #         client_socket.send("SUCCESS".encode('utf-8'))
    #         print(f"  文件保存成功: {save_path}")
    #     except Exception as e:
    #         print(f"  处理客户端错误: {e}")
    #         client_socket.send("ERROR".encode('utf-8'))
    #     finally:
    #         client_socket.close()
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)  # 设置 accept() 超时 1 秒,以便KeyboardInterrupt

        print(f" 服务器启动在 {self.host}:{self.port}")
        print(" 等待客户端连接...")
        try:
            while True:
                try:
                    client_socket, client_addr = self.server_socket.accept()
                except socket.timeout:
                    continue  # 超时后继续循环，此时可以检查 KeyboardInterrupt

                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_addr)
                )
                client_thread.daemon = True
                client_thread.start()

        except KeyboardInterrupt:
            print("\n 服务器关闭")
        finally:
            self.server_socket.close()
if __name__ == "__main__":
    server = ImageServer()
    server.start_server()