import cv2
import asyncio
import struct
import pickle
from concurrent.futures import ThreadPoolExecutor

class AsyncCameraClient:
    def __init__(self, server_host='127.0.0.1', server_port=8888):
        self.server_host = server_host
        self.server_port = server_port
        self.camera = None
        self.is_streaming = False
        self.frame_queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.writer = None
        self.reader = None
        
    async def connect_to_server(self):
        """异步连接到服务器"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            print(f"连接到视频服务器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def init_camera_sync(self):
        """同步初始化摄像头（在线程池中运行）"""
        try:
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.camera.isOpened():
                print("尝试其他摄像头索引...")
                self.camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
                
            if not self.camera.isOpened():
                print("无法打开摄像头")
                return False
                
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            print("摄像头初始化成功")
            return True
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False
    
    async def init_camera(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.init_camera_sync)
    
    async def capture_frames_async(self):
        print("开始异步帧捕获...")
        while self.is_streaming:
            try:
                # 在单独的线程中读取帧，避免阻塞事件循环
                loop = asyncio.get_event_loop()
                ret, frame = await loop.run_in_executor(
                    self.executor, 
                    self.camera.read
                )
                if not ret:
                    print("无法读取帧")
                    await asyncio.sleep(0.1)
                    continue
                # 异步显示帧
                asyncio.create_task(self.display_frame_async(frame))
                # 压缩帧（CPU密集型，在线程池中运行）
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
                print(f"捕获帧时出错: {e}")
                await asyncio.sleep(0.1)
    
    def encode_frame(self, frame):
        _, buffer = cv2.imencode('.jpg', frame, [
            cv2.IMWRITE_JPEG_QUALITY, 
            80
        ])
        data = pickle.dumps(buffer)
        return struct.pack("Q", len(data)) + data
    
    async def display_frame_async(self, frame):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.display_frame_sync,
            frame
        )
    
    def display_frame_sync(self, frame):
        try:
            cv2.imshow('Async Camera Stream', frame)
            cv2.waitKey(1)
        except Exception as e:
            print(f"显示帧时出错: {e}")
    
    async def send_frames_async(self):
        print("开始异步发送帧...")
        
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
                print(f"发送帧时出错: {e}")
                break
    
    async def handle_keyboard_input(self):
        print("按 'q' 键停止...")
        
        try:
            while self.is_streaming:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
    
    async def start_streaming(self):
        print("启动异步视频流客户端...")
        
        # 1. 异步初始化摄像头
        print("1. 初始化摄像头...")
        if not await self.init_camera():
            return False
        
        # 2. 异步连接到服务器
        print("2. 连接到服务器...")
        if not await self.connect_to_server():
            self.camera.release()
            return False
        
        self.is_streaming = True
        
        # 3. 创建异步任务
        print("3. 启动异步任务...")
        tasks = [
            asyncio.create_task(self.capture_frames_async()),
            asyncio.create_task(self.send_frames_async()),
            asyncio.create_task(self.handle_keyboard_input()),
        ]
        print("视频流传输开始")
        try:
            # 等待任意任务完成（或出错）
            done, pending = await asyncio.wait(
                tasks, 
                return_when=asyncio.FIRST_COMPLETED
            )
            # 检查是否有任务出错
            for task in done:
                if task.exception():
                    print(f"任务出错: {task.exception()}")
        except KeyboardInterrupt:
            print("接收到中断信号")
        finally:
            await self.cleanup()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def cleanup(self):
        print("清理资源...")
        self.is_streaming = False
        if self.camera:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self.camera.release
            )
        
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except:
                pass
        
        # 在线程中关闭窗口
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            cv2.destroyAllWindows
        )
        
        self.executor.shutdown(wait=False)
        print("资源清理完成")

async def main():
    """主异步函数"""
    print("=" * 50)
    print("异步视频流客户端")
    print("=" * 50)
    
    client = AsyncCameraClient()
    
    try:
        await client.start_streaming()
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        print("=" * 50)
        print("程序结束")
        print("=" * 50)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")