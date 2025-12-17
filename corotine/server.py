# import socket
# import threading
# import cv2
# import pickle
# import struct
# from datetime import datetime
# import os
# import asyncio
# from concurrent.futures import ThreadPoolExecutor

# class VideoStreamServer:
#     def __init__(self, host='0.0.0.0', port=8888, save_dir='videos'):
#         self.host = host  # 监听地址（0.0.0.0表示所有网络接口）
#         self.port = port  # 监听端口
#         self.save_dir = save_dir  # 视频保存目录
#         self.server = None  # 服务器对象占位
#         self.clients = []  # 客户端列表（未实际使用）
#         self.executor = ThreadPoolExecutor(max_workers=4)  # 4线程的线程池，用于处  理阻塞操作
#         self.ensure_directory()  # 确保存储目录存在
    
#     def ensure_directory(self):
#         if not os.path.exists(self.save_dir):
#             os.makedirs(self.save_dir)
#             print(f"  创建视频存储目录: {self.save_dir}")
    
#     async def handle_video_client(self, reader, writer):
#         client_addr = writer.get_extra_info('peername')
#         print(f"  视频客户端连接: {client_addr}")
        
#         data = b""# 初始化数据缓冲区
#         payload_size = struct.calcsize("Q") # 计算'Q'（无符号长整型）的字节数（8字节），用于帧大小
        
#         # 视频录制相关变量
#         video_writer = None
#         frame_width = 640  # 默认宽度
#         frame_height = 480  # 默认高度
#         fps = 30  # 帧率
#         fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4编码
#         is_first_frame = True# 标记是否为第一帧
#         frame_count = 0
        
#         try:
#             while True:
#                 # 接收帧大小
#                 while len(data) < payload_size:
#                     packet = await reader.read(4096)
#                     if not packet:
#                         return
#                     data += packet
#                 # 提取帧大小信息
#                 packed_msg_size = data[:payload_size]# 取出前8字节（帧大小）
#                 data = data[payload_size:]# 移除已处理的数据
#                 msg_size = struct.unpack("Q", packed_msg_size)[0]# 解包得到实际帧大小
                
#                 # 接收帧数据
#                 while len(data) < msg_size:
#                     data += await reader.read(4096)
                
#                 frame_data = data[:msg_size]
#                 data = data[msg_size:]
                
#                 # 反序列化帧
#                 frame = pickle.loads(frame_data)
                
#                 # 在线程池中解码帧（避免阻塞事件循环）
#                 loop = asyncio.get_event_loop()
#                 frame = await loop.run_in_executor(
#                     self.executor,
#                     self.decode_frame,
#                     frame
#                 )
                
#                 if frame is not None:
#                     frame_count += 1
                    
#                     # 如果是第一帧，初始化视频写入器
#                     if is_first_frame:
#                         frame_height, frame_width = frame.shape[:2]
#                         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                         video_filename = f"video_{client_addr[0]}_{timestamp}.mp4"
#                         video_path = os.path.join(self.save_dir, video_filename)
                        
#                         # 在线程池中创建视频写入器
#                         video_writer = await loop.run_in_executor(
#                             self.executor,
#                             self.create_video_writer,
#                             video_path, fourcc, fps, frame_width, frame_height
#                         )
                        
#                         if video_writer is not None:
#                             print(f"  开始录制视频: {video_filename}")
#                             is_first_frame = False
#                         else:
#                             print(f"  无法创建视频文件: {video_path}")
                    
#                     # 写入帧到视频文件
#                     if video_writer is not None:
#                         await loop.run_in_executor(
#                             self.executor,
#                             self.write_frame_to_video,
#                             video_writer, frame
#                         )
                    
#                     # 显示帧（可选）- 每10帧显示一次以减少负载
#                     if frame_count % 10 == 0:
#                         await loop.run_in_executor(
#                             self.executor,
#                             self.display_frame,
#                             frame, client_addr
#                         )
        
#         except Exception as e:
#             print(f"  视频流处理错误: {e}")
#         finally:
#             # 释放视频写入器
#             if video_writer is not None:
#                 await self.release_video_writer(video_writer)
#                 print(f"  视频保存完成，共 {frame_count} 帧")
            
#             # 关闭连接
#             writer.close()
#             try:
#                 await writer.wait_closed()
#             except:
#                 pass
            
#             # 关闭显示窗口
#             await self.close_display_window()
            
#             print(f"  视频客户端断开: {client_addr}")
    
#     def decode_frame(self, frame_data):
#         try:
#             return cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
#         except Exception as e:
#             print(f"  解码帧时出错: {e}")
#             return None
    
#     def create_video_writer(self, video_path, fourcc, fps, width, height):
#         try:
#             video_writer = cv2.VideoWriter(
#                 video_path, 
#                 fourcc, 
#                 fps, 
#                 (width, height)
#             )
            
#             if video_writer.isOpened():
#                 return video_writer
#             else:
#                 return None
#         except Exception as e:
#             print(f"  创建视频写入器时出错: {e}")
#             return None
    
#     def write_frame_to_video(self, video_writer, frame):
#         try:
#             video_writer.write(frame)
#         except Exception as e:
#             print(f"  写入帧到视频时出错: {e}")
    
#     def display_frame(self, frame, client_addr):
#         try:
#             cv2.imshow(f"Video from {client_addr}", frame)
#             cv2.waitKey(1)
#         except Exception as e:
#             print(f"  显示帧时出错: {e}")
    
#     async def release_video_writer(self, video_writer):
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(
#             self.executor,
#             video_writer.release
#         )
    
#     async def close_display_window(self):
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(
#             self.executor,
#             cv2.destroyAllWindows
#         )
    
#     async def start_video_server(self):
#         self.server = await asyncio.start_server(
#             self.handle_video_client,
#             self.host,
#             self.port
#         )
        
#         addr = self.server.sockets[0].getsockname()
#         print(f"  视频流服务器启动在 {addr}")
        
#         try:
#             async with self.server:
#                 await self.server.serve_forever()
#         except asyncio.CancelledError:
#             print("\n  视频服务器关闭")
#         finally:
#             if self.server:
#                 self.server.close()
#                 await self.server.wait_closed()
            
#             # 关闭线程池
#             self.executor.shutdown(wait=True)

# async def main():
#     video_server = VideoStreamServer()
#     await video_server.start_video_server()

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\n服务器已停止")

import cv2
import pickle
import struct
import asyncio
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class VideoStreamServer:
    def __init__(self, host='0.0.0.0', port=8888, save_dir='videos'):
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self.server = None
        self.active_connections = {}  # 跟踪活动连接
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.ensure_directory()
    
    def ensure_directory(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"创建视频存储目录: {self.save_dir}")
    
    async def handle_video_client(self, reader, writer):
        client_addr = writer.get_extra_info('peername')
        client_id = f"{client_addr[0]}:{client_addr[1]}"
        
        print(f"新客户端连接: {client_id}")
        self.active_connections[client_id] = {
            'writer': writer,
            'frame_count': 0,
            'video_writer': None,
            'is_recording': True
        }
        
        data = b""
        payload_size = struct.calcsize("Q")
        
        video_writer = None
        frame_width = 640
        frame_height = 480
        fps = 30
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        is_first_frame = True
        
        try:
            while self.active_connections.get(client_id, {}).get('is_recording', True):
                # 接收帧大小
                while len(data) < payload_size:
                    packet = await reader.read(4096)
                    if not packet:
                        return
                    data += packet
                
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]
                
                # 接收帧数据
                while len(data) < msg_size:
                    data += await reader.read(4096)
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                # 反序列化帧
                frame = pickle.loads(frame_data)
                
                # 在线程池中解码帧
                loop = asyncio.get_event_loop()
                frame = await loop.run_in_executor(
                    self.executor,
                    self.decode_frame,
                    frame
                )
                
                if frame is not None:
                    self.active_connections[client_id]['frame_count'] += 1
                    frame_count = self.active_connections[client_id]['frame_count']
                    
                    # 如果是第一帧，初始化视频写入器
                    if is_first_frame:
                        frame_height, frame_width = frame.shape[:2]
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        video_filename = f"video_{client_addr[0]}_{timestamp}.mp4"
                        video_path = os.path.join(self.save_dir, video_filename)
                        
                        video_writer = await loop.run_in_executor(
                            self.executor,
                            self.create_video_writer,
                            video_path, fourcc, fps, frame_width, frame_height
                        )
                        
                        if video_writer is not None:
                            self.active_connections[client_id]['video_writer'] = video_writer
                            print(f"开始录制: {video_filename}")
                            is_first_frame = False
                    
                    # 写入帧到视频文件
                    if video_writer is not None:
                        await loop.run_in_executor(
                            self.executor,
                            self.write_frame_to_video,
                            video_writer, frame
                        )
                    
                    # 显示帧（每10帧显示一次）
                    if frame_count % 10 == 0:
                        await loop.run_in_executor(
                            self.executor,
                            self.display_frame,
                            frame, client_addr
                        )
        
        except (ConnectionError, asyncio.CancelledError):
            print(f"客户端断开: {client_id}")
        except Exception as e:
            print(f"视频流处理错误: {e}")
        finally:
            # 清理资源
            if client_id in self.active_connections:
                # 释放视频写入器
                video_writer = self.active_connections[client_id].get('video_writer')
                if video_writer is not None:
                    await loop.run_in_executor(self.executor, video_writer.release)
                    print(f"视频保存完成: {client_id}, 共 {frame_count} 帧")
                
                del self.active_connections[client_id]
            
            # 关闭连接
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass
            
            # 关闭显示窗口
            await self.close_display_window()
            print(f"客户端清理完成: {client_id}")
    
    def decode_frame(self, frame_data):
        try:
            return cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"解码帧时出错: {e}")
            return None
    
    def create_video_writer(self, video_path, fourcc, fps, width, height):
        try:
            video_writer = cv2.VideoWriter(
                video_path, 
                fourcc, 
                fps, 
                (width, height)
            )
            return video_writer if video_writer.isOpened() else None
        except Exception as e:
            print(f"创建视频写入器时出错: {e}")
            return None
    
    def write_frame_to_video(self, video_writer, frame):
        try:
            video_writer.write(frame)
        except Exception as e:
            print(f"写入帧到视频时出错: {e}")
    
    def display_frame(self, frame, client_addr):
        try:
            cv2.imshow(f"Video from {client_addr[0]}:{client_addr[1]}", frame)
            cv2.waitKey(1)
        except Exception as e:
            pass  # 静默处理显示错误
    
    async def close_display_window(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, cv2.destroyAllWindows)
    
    async def start_video_server(self):
        self.server = await asyncio.start_server(
            self.handle_video_client,
            self.host,
            self.port
        )
        
        addr = self.server.sockets[0].getsockname()
        print(f"视频流服务器启动在 {addr}")
        print("=" * 50)
        
        try:
            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            print("\n视频服务器关闭")
        finally:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            self.executor.shutdown(wait=True)

async def main():
    video_server = VideoStreamServer()
    await video_server.start_video_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务器已停止")