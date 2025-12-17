import socket
import os

class ImageClient:
    def __init__(self, server_host='127.0.0.1', server_port=8888):
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
    
    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_host, self.server_port))
            print(f"  连接到服务器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"  连接失败: {e}")
            return False
    
    def send_image_file(self, image_path):
        if not os.path.exists(image_path):
            print(f"  文件不存在: {image_path}")
            return False
        
        try:
            # 获取文件信息
            filename = os.path.basename(image_path)
            file_size = os.path.getsize(image_path)
            
            # 发送文件信息
            file_info = f"{filename}:{file_size}"
            self.client_socket.send(len(file_info).to_bytes(4, byteorder='big'))
            self.client_socket.send(file_info.encode('utf-8'))
            
            # 发送文件数据
            with open(image_path, 'rb') as f:
                sent_size = 0
                while sent_size < file_size:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.client_socket.send(chunk)
                    sent_size += len(chunk)
            
            # 等待服务器响应
            response = self.client_socket.recv(1024).decode('utf-8')
            if response == "SUCCESS":
                print(f"  文件发送成功: {filename}")
                return True
            else:
                print(f"  文件发送失败")
                return False
                
        except Exception as e:
            print(f"  发送过程错误: {e}")
            return False
        finally:
            self.client_socket.close()
    
    def upload_image(self, image_path):
        if self.connect_to_server():
            return self.send_image_file(image_path)
        return False

if __name__ == "__main__":
    client = ImageClient()
    # 上传测试图像
    client.upload_image('test_image.png')