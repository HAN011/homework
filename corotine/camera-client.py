# import cv2
# import asyncio
# import struct
# import pickle
# from concurrent.futures import ThreadPoolExecutor

# class AsyncCameraClient:
#     def __init__(self, server_host='127.0.0.1', server_port=8888):
#         self.server_host = server_host
#         self.server_port = server_port
#         self.camera = None
#         self.is_streaming = False
#         self.frame_queue = asyncio.Queue(maxsize=10)
#         self.executor = ThreadPoolExecutor(max_workers=2)
#         self.writer = None
#         self.reader = None
        
#     async def connect_to_server(self):
#         """异步连接到服务器"""
#         try:
#             self.reader, self.writer = await asyncio.open_connection(
#                 self.server_host, self.server_port
#             )
#             print(f"连接到视频服务器 {self.server_host}:{self.server_port}")
#             return True
#         except Exception as e:
#             print(f"连接失败: {e}")
#             return False
    
#     def init_camera_sync(self):
#         """同步初始化摄像头（在线程池中运行）"""
#         try:
#             self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#             if not self.camera.isOpened():
#                 print("尝试其他摄像头索引...")
#                 self.camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                
#             if not self.camera.isOpened():
#                 print("无法打开摄像头")
#                 return False
                
#             # 设置摄像头参数
#             self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
#             self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
#             self.camera.set(cv2.CAP_PROP_FPS, 30)
            
#             print("摄像头初始化成功")
#             return True
#         except Exception as e:
#             print(f"摄像头初始化失败: {e}")
#             return False
    
#     async def init_camera(self):
#         loop = asyncio.get_event_loop()
#         return await loop.run_in_executor(self.executor, self.init_camera_sync)
    
#     async def capture_frames_async(self):
#         print("开始异步帧捕获...")
#         while self.is_streaming:
#             try:
#                 # 在单独的线程中读取帧，避免阻塞事件循环
#                 loop = asyncio.get_event_loop()
#                 ret, frame = await loop.run_in_executor(
#                     self.executor, 
#                     self.camera.read
#                 )
#                 if not ret:
#                     print("无法读取帧")
#                     await asyncio.sleep(0.1)
#                     continue
#                 # 异步显示帧
#                 asyncio.create_task(self.display_frame_async(frame))
#                 # 压缩帧（CPU密集型，在线程池中运行）
#                 encoded_frame = await loop.run_in_executor(
#                     self.executor,
#                     self.encode_frame,
#                     frame
#                 )
#                 # 放入队列供发送
#                 if not self.frame_queue.full():
#                     await self.frame_queue.put(encoded_frame)
#                 # 控制帧率
#                 await asyncio.sleep(0.033)  # ~30 FPS
                
#             except asyncio.CancelledError:
#                 break
#             except Exception as e:
#                 print(f"捕获帧时出错: {e}")
#                 await asyncio.sleep(0.1)
    
#     def encode_frame(self, frame):
#         _, buffer = cv2.imencode('.jpg', frame, [
#             cv2.IMWRITE_JPEG_QUALITY, 
#             80
#         ])
#         data = pickle.dumps(buffer)
#         return struct.pack("Q", len(data)) + data
    
#     async def display_frame_async(self, frame):
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(
#             self.executor,
#             self.display_frame_sync,
#             frame
#         )
    
#     def display_frame_sync(self, frame):
#         try:
#             cv2.imshow('Async Camera Stream', frame)
#             cv2.waitKey(1)
#         except Exception as e:
#             print(f"显示帧时出错: {e}")
    
#     async def send_frames_async(self):
#         print("开始异步发送帧...")
        
#         while self.is_streaming:
#             try:
#                 # 从队列获取帧（带有超时）
#                 try:
#                     frame_data = await asyncio.wait_for(
#                         self.frame_queue.get(),
#                         timeout=0.5
#                     )
#                 except asyncio.TimeoutError:
#                     await asyncio.sleep(0.01)
#                     continue
                
#                 # 异步发送数据
#                 self.writer.write(frame_data)
#                 await self.writer.drain()
                
#             except (asyncio.CancelledError, ConnectionError):
#                 break
#             except Exception as e:
#                 print(f"发送帧时出错: {e}")
#                 break
    
#     async def handle_keyboard_input(self):
#         print("按 'q' 键停止...")
        
#         try:
#             while self.is_streaming:
#                 await asyncio.sleep(0.1)
#         except asyncio.CancelledError:
#             pass
    
#     async def start_streaming(self):
#         print("启动异步视频流客户端...")
        
#         # 1. 异步初始化摄像头
#         print("1. 初始化摄像头...")
#         if not await self.init_camera():
#             return False
        
#         # 2. 异步连接到服务器
#         print("2. 连接到服务器...")
#         if not await self.connect_to_server():
#             self.camera.release()
#             return False
        
#         self.is_streaming = True
        
#         # 3. 创建异步任务
#         print("3. 启动异步任务...")
#         tasks = [
#             asyncio.create_task(self.capture_frames_async()),
#             asyncio.create_task(self.send_frames_async()),
#             asyncio.create_task(self.handle_keyboard_input()),
#         ]
#         print("视频流传输开始")
#         try:
#             # 等待任意任务完成（或出错）
#             done, pending = await asyncio.wait(
#                 tasks, 
#                 return_when=asyncio.FIRST_COMPLETED
#             )
#             # 检查是否有任务出错
#             for task in done:
#                 if task.exception():
#                     print(f"任务出错: {task.exception()}")
#         except KeyboardInterrupt:
#             print("接收到中断信号")
#         finally:
#             await self.cleanup()
#             for task in tasks:
#                 if not task.done():
#                     task.cancel()
#             await asyncio.gather(*tasks, return_exceptions=True)
    
#     async def cleanup(self):
#         print("清理资源...")
#         self.is_streaming = False
#         if self.camera:
#             loop = asyncio.get_event_loop()
#             await loop.run_in_executor(
#                 self.executor,
#                 self.camera.release
#             )
        
#         if self.writer:
#             self.writer.close()
#             try:
#                 await self.writer.wait_closed()
#             except:
#                 pass
        
#         # 在线程中关闭窗口
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(
#             self.executor,
#             cv2.destroyAllWindows
#         )
        
#         self.executor.shutdown(wait=False)
#         print("资源清理完成")

# async def main():
#     """主异步函数"""
#     print("=" * 50)
#     print("异步视频流客户端")
#     print("=" * 50)
    
#     client = AsyncCameraClient()
    
#     try:
#         await client.start_streaming()
#     except Exception as e:
#         print(f"程序运行出错: {e}")
#     finally:
#         print("=" * 50)
#         print("程序结束")
#         print("=" * 50)

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\n程序被用户中断")

import cv2
import asyncio
import struct
import pickle
import signal
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
import argparse

class AsyncCameraClient:
    def __init__(self, camera_id: int, server_host='127.0.0.1', server_port=8888):
        self.camera_id = camera_id
        self.server_host = server_host
        self.server_port = server_port
        self.camera = None
        self.is_streaming = False
        self.frame_queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.writer = None
        self.reader = None
        self.task = None
        
    async def connect_to_server(self):
        """异步连接到服务器"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            print(f"[摄像头{self.camera_id}] 连接到服务器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"[摄像头{self.camera_id}] 连接失败: {e}")
            return False
    
    def init_camera_sync(self):
        """同步初始化摄像头"""
        try:
            # 尝试打开摄像头
            self.camera = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
            
            if not self.camera.isOpened():
                print(f"[摄像头{self.camera_id}] 无法打开摄像头")
                return False
                
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            print(f"[摄像头{self.camera_id}] 初始化成功")
            return True
        except Exception as e:
            print(f"[摄像头{self.camera_id}] 摄像头初始化失败: {e}")
            return False
    
    async def init_camera(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.init_camera_sync)
    
    async def capture_frames_async(self):
        """异步捕获帧"""
        print(f"[摄像头{self.camera_id}] 开始帧捕获...")
        while self.is_streaming:
            try:
                # 在单独的线程中读取帧
                loop = asyncio.get_event_loop()
                ret, frame = await loop.run_in_executor(
                    self.executor, 
                    self.camera.read
                )
                if not ret:
                    print(f"[摄像头{self.camera_id}] 无法读取帧")
                    await asyncio.sleep(0.1)
                    continue
                
                # 显示帧
                asyncio.create_task(self.display_frame_async(frame))
                
                # 压缩帧
                encoded_frame = await loop.run_in_executor(
                    self.executor,
                    self.encode_frame,
                    frame
                )
                
                # 放入队列供发送
                if not self.frame_queue.full():
                    await self.frame_queue.put(encoded_frame)
                
                # 控制帧率
                await asyncio.sleep(0.033)  # ~30 FPS
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[摄像头{self.camera_id}] 捕获帧时出错: {e}")
                await asyncio.sleep(0.1)
    
    def encode_frame(self, frame):
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        data = pickle.dumps(buffer)
        return struct.pack("Q", len(data)) + data
    
    async def display_frame_async(self, frame):
        """异步显示帧"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.display_frame_sync,
            frame
        )
    
    def display_frame_sync(self, frame):
        """同步显示帧"""
        try:
            cv2.imshow(f'摄像头 {self.camera_id}', frame)
            cv2.waitKey(1)
        except Exception as e:
            pass  # 静默处理显示错误
    
    async def send_frames_async(self):
        """异步发送帧"""
        print(f"[摄像头{self.camera_id}] 开始发送帧...")
        
        while self.is_streaming:
            try:
                # 从队列获取帧（带有超时）
                try:
                    frame_data = await asyncio.wait_for(
                        self.frame_queue.get(),
                        timeout=0.5
                    )
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.01)
                    continue
                
                # 异步发送数据
                self.writer.write(frame_data)
                await self.writer.drain()
                
            except (asyncio.CancelledError, ConnectionError):
                break
            except Exception as e:
                print(f"[摄像头{self.camera_id}] 发送帧时出错: {e}")
                break
    
    async def start_streaming(self):
        """启动流传输"""
        print(f"\n[摄像头{self.camera_id}] 启动视频流...")
        
        # 1. 初始化摄像头
        if not await self.init_camera():
            return False
        
        # 2. 连接到服务器
        if not await self.connect_to_server():
            await self.cleanup()
            return False
        
        self.is_streaming = True
        
        # 3. 创建异步任务
        capture_task = asyncio.create_task(self.capture_frames_async())
        send_task = asyncio.create_task(self.send_frames_async())
        
        try:
            # 等待任意任务完成
            done, pending = await asyncio.wait(
                [capture_task, send_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 检查是否有任务出错
            for task in done:
                if task.exception():
                    print(f"[摄像头{self.camera_id}] 任务出错: {task.exception()}")
                    
        except KeyboardInterrupt:
            print(f"\n[摄像头{self.camera_id}] 接收到中断信号")
        finally:
            await self.cleanup()
            
            # 取消所有任务
            for task in [capture_task, send_task]:
                if not task.done():
                    task.cancel()
            
            # 等待任务完成
            await asyncio.gather(capture_task, send_task, return_exceptions=True)
            print(f"[摄像头{self.camera_id}] 已停止")
    
    async def stop(self):
        """停止摄像头流"""
        print(f"[摄像头{self.camera_id}] 正在停止...")
        self.is_streaming = False
    
    async def cleanup(self):
        """清理资源"""
        print(f"[摄像头{self.camera_id}] 清理资源...")
        self.is_streaming = False
        
        # 释放摄像头
        if self.camera:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self.camera.release)
        
        # 关闭连接
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except:
                pass
        
        # 关闭窗口
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            lambda: cv2.destroyWindow(f'摄像头 {self.camera_id}')
        )
        
        self.executor.shutdown(wait=False)


class MultiCameraManager:
    """多摄像头管理器"""
    def __init__(self):
        self.cameras: Dict[int, AsyncCameraClient] = {}
        self.camera_tasks: Dict[int, asyncio.Task] = {}
        self.running = True
        
    async def add_camera(self, camera_id: int, server_host='127.0.0.1', server_port=8888):
        """添加摄像头"""
        if camera_id in self.cameras:
            print(f"摄像头 {camera_id} 已在运行中")
            return False
        
        client = AsyncCameraClient(camera_id, server_host, server_port)
        self.cameras[camera_id] = client
        
        # 创建摄像头任务
        task = asyncio.create_task(client.start_streaming(), name=f"camera_{camera_id}")
        self.camera_tasks[camera_id] = task
        
        print(f"已添加摄像头 {camera_id}")
        return True
    
    async def stop_camera(self, camera_id: int):
        """停止特定摄像头"""
        if camera_id not in self.cameras:
            print(f"摄像头 {camera_id} 不存在")
            return False
        
        client = self.cameras[camera_id]
        await client.stop()
        
        # 等待任务完成
        task = self.camera_tasks[camera_id]
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()
        
        # 清理
        del self.cameras[camera_id]
        del self.camera_tasks[camera_id]
        
        print(f"摄像头 {camera_id} 已停止")
        return True
    
    async def stop_all(self):
        """停止所有摄像头"""
        print("\n正在停止所有摄像头...")
        
        # 停止所有摄像头客户端
        for camera_id in list(self.cameras.keys()):
            await self.stop_camera(camera_id)
        
        print("所有摄像头已停止")
    
    def list_cameras(self):
        """列出所有摄像头"""
        if not self.cameras:
            print("没有正在运行的摄像头")
            return []
        
        print("\n当前运行的摄像头:")
        for camera_id in self.cameras.keys():
            print(f"  - 摄像头 {camera_id}")
        return list(self.cameras.keys())
    
    async def run_command_interface(self):
        """运行命令界面"""
        print("\n" + "="*50)
        print("多摄像头客户端管理器")
        print("="*50)
        print("命令:")
        print("  list      - 列出所有摄像头")
        print("  add <id>  - 添加摄像头 (例如: add 0)")
        print("  stop <id> - 停止摄像头 (例如: stop 0)")
        print("  stopall   - 停止所有摄像头")
        print("  exit      - 退出程序")
        print("="*50)
        
        while self.running:
            try:
                # 异步读取用户输入
                loop = asyncio.get_event_loop()
                command = await loop.run_in_executor(None, input, "\n请输入命令: ")
                command = command.strip().lower()
                
                if command == "exit":
                    await self.stop_all()
                    self.running = False
                    break
                    
                elif command == "list":
                    self.list_cameras()
                    
                elif command.startswith("add "):
                    try:
                        camera_id = int(command.split()[1])
                        await self.add_camera(camera_id)
                    except (IndexError, ValueError):
                        print("用法: add <摄像头ID>")
                        
                elif command.startswith("stop "):
                    try:
                        camera_id = int(command.split()[1])
                        await self.stop_camera(camera_id)
                    except (IndexError, ValueError):
                        print("用法: stop <摄像头ID>")
                        
                elif command == "stopall":
                    await self.stop_all()
                    
                elif command:
                    print("未知命令")
                    
            except KeyboardInterrupt:
                print("\n\n检测到 Ctrl+C，准备退出...")
                await self.stop_all()
                self.running = False
                break
            except EOFError:
                print("\n检测到 EOF，准备退出...")
                await self.stop_all()
                self.running = False
                break
    
    async def run(self):
        """运行管理器"""
        try:
            # 运行命令界面
            await self.run_command_interface()
        except Exception as e:
            print(f"管理器运行出错: {e}")
        finally:
            # 确保所有资源都被清理
            await self.stop_all()
            cv2.destroyAllWindows()
            print("程序结束")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多摄像头客户端管理器')
    parser.add_argument('--server', default='127.0.0.1', help='服务器地址')
    parser.add_argument('--port', type=int, default=8888, help='服务器端口')
    args = parser.parse_args()
    
    manager = MultiCameraManager()
    await manager.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")