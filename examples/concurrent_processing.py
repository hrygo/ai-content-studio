"""
并发执行优化示例
基于 minimax_aipodcast 的生产者-消费者模式
"""
import threading
import queue
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class ConcurrentProcessor:
    """并发处理器"""

    def __init__(self, max_workers: int = 3):
        """
        初始化并发处理器

        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.errors = []
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0
        }

    def worker(self, processor_func: Callable):
        """
        工作线程函数

        Args:
            processor_func: 处理函数
        """
        while True:
            task = self.task_queue.get()
            if task is None:  # 终止信号
                self.task_queue.task_done()
                break

            try:
                task_id, task_data = task
                result = processor_func(task_data)
                self.result_queue.put((task_id, result))
                self.stats["tasks_completed"] += 1
            except Exception as e:
                logger.error(f"任务 {task_id} 失败: {e}")
                self.errors.append((task_id, str(e)))
                self.stats["tasks_failed"] += 1
            finally:
                self.task_queue.task_done()

    def submit_tasks(self, tasks: List[tuple]):
        """
        提交任务列表

        Args:
            tasks: 任务列表 [(task_id, task_data), ...]
        """
        for task in tasks:
            self.task_queue.put(task)
            self.stats["tasks_submitted"] += 1

    def process_concurrent(self, processor_func: Callable, tasks: List[tuple]) -> Dict[str, Any]:
        """
        并发处理任务

        Args:
            processor_func: 处理函数
            tasks: 任务列表

        Returns:
            结果字典 {task_id: result}
        """
        # 提交任务
        self.submit_tasks(tasks)

        # 启动工作线程
        threads = []
        for i in range(self.max_workers):
            t = threading.Thread(target=self.worker, args=(processor_func,))
            t.start()
            threads.append(t)

        # 等待所有任务完成
        self.task_queue.join()

        # 发送终止信号
        for _ in range(self.max_workers):
            self.task_queue.put(None)

        # 等待所有线程结束
        for t in threads:
            t.join()

        # 收集结果
        results = {}
        while not self.result_queue.empty():
            task_id, result = self.result_queue.get()
            results[task_id] = result

        return results


class StreamPipeline:
    """流式处理管道（生产者-消费者模式）"""

    def __init__(self, buffer_size: int = 10):
        """
        初始化流式管道

        Args:
            buffer_size: 缓冲区大小
        """
        self.data_queue = queue.Queue(maxsize=buffer_size)
        self.completed = False
        self.errors = []

    def producer(self, generator_func: Callable):
        """
        生产者线程：从生成器读取数据

        Args:
            generator_func: 数据生成函数（生成器）
        """
        try:
            for item in generator_func():
                self.data_queue.put(item)
        except Exception as e:
            logger.error(f"生产者错误: {e}")
            self.errors.append(str(e))
        finally:
            self.completed = True
            # 发送完成信号
            self.data_queue.put(None)

    def consumer(self, processor_func: Callable) -> List[Any]:
        """
        消费者线程：处理数据

        Args:
            processor_func: 数据处理函数

        Returns:
            处理结果列表
        """
        results = []
        while True:
            item = self.data_queue.get()
            if item is None:  # 完成信号
                break

            try:
                result = processor_func(item)
                results.append(result)
            except Exception as e:
                logger.error(f"消费者错误: {e}")
                self.errors.append(str(e))
            finally:
                self.data_queue.task_done()

        return results

    def run_pipeline(self, generator_func: Callable, processor_func: Callable) -> List[Any]:
        """
        运行管道

        Args:
            generator_func: 数据生成函数
            processor_func: 数据处理函数

        Returns:
            处理结果列表
        """
        # 启动生产者线程
        producer_thread = threading.Thread(
            target=self.producer,
            args=(generator_func,)
        )
        producer_thread.start()

        # 主线程作为消费者
        results = self.consumer(processor_func)

        # 等待生产者结束
        producer_thread.join()

        return results


# 使用示例

def example_concurrent_tts():
    """示例：并发 TTS 合成"""
    from services.api_client import create_minimax_client

    client = create_minimax_client()
    processor = ConcurrentProcessor(max_workers=3)

    # 准备任务
    texts = [
        "这是第一段文本",
        "这是第二段文本",
        "这是第三段文本",
    ]
    tasks = [(f"text_{i}", text) for i, text in enumerate(texts)]

    # 定义处理函数
    def process_tts(task_data):
        text, output_file = task_data
        audio_bytes = client.text_to_speech(text=text)
        if audio_bytes:
            with open(output_file, "wb") as f:
                f.write(audio_bytes)
            return output_file
        return None

    # 并发处理
    results = processor.process_concurrent(process_tts, tasks)
    print(f"处理完成: {results}")
    print(f"统计信息: {processor.stats}")


def example_stream_pipeline():
    """示例：流式 LLM + TTS 管道"""
    from services.api_client import create_minimax_client

    client = create_minimax_client()
    pipeline = StreamPipeline(buffer_size=5)

    # 定义生成器函数（LLM 流式生成）
    def generate_sentences():
        for chunk in client.generate_text_stream("请生成一段播客脚本"):
            yield chunk

    # 定义处理函数（TTS 合成）
    def synthesize_audio(chunk):
        # 这里可以添加缓存逻辑
        audio_bytes = client.text_to_speech(text=chunk)
        return audio_bytes

    # 运行管道
    audio_chunks = pipeline.run_pipeline(generate_sentences, synthesize_audio)
    print(f"生成了 {len(audio_chunks)} 个音频片段")


if __name__ == "__main__":
    # 运行示例
    print("=== 并发 TTS 示例 ===")
    example_concurrent_tts()

    print("\n=== 流式管道示例 ===")
    example_stream_pipeline()
