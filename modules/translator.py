"""
实时翻译模块
===========
基于Hugging Face Transformers实现实时机器翻译
支持SimulTrans策略进行同步翻译
"""

import re
import time
import threading
import queue
from typing import Optional, Callable, List, Dict
import asyncio

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError as e:
    print(f"翻译依赖库未安装: {e}")
    print("请运行: pip install torch transformers")

from config.settings import config
from models.model_manager import model_manager


class SimulTransStrategy:
    """同步翻译策略 - 实现增量翻译"""

    def __init__(self, chunk_size: int = 128, overlap: int = 32):
        """
        初始化SimulTrans策略

        Args:
            chunk_size: 翻译块大小（字符数）
            overlap: 重叠字符数，用于保持上下文
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.previous_context = ""
        self.translated_cache = {}

    def should_translate(self, text: str, is_final: bool = False) -> bool:
        """判断是否应该进行翻译"""
        # 如果是最终文本，总是翻译
        if is_final:
            return True

        # 如果文本长度达到阈值，进行翻译
        if len(text) >= self.chunk_size:
            return True

        # 如果文本包含句子结束标记，进行翻译
        sentence_endings = re.search(r'[.!?。！？]', text)
        if sentence_endings:
            return True

        return False

    def prepare_text_for_translation(self, new_text: str, is_final: bool = False) -> Optional[str]:
        """
        准备翻译文本，处理增量输入

        Args:
            new_text: 新的输入文本
            is_final: 是否为最终文本

        Returns:
            需要翻译的文本块，如果不需要翻译则返回None
        """
        if not self.should_translate(new_text, is_final):
            return None

        # 如果是最终文本或者是完整句子，直接翻译
        if is_final or re.search(r'[.!?。！？]$', new_text.strip()):
            text_to_translate = new_text
            self.previous_context = ""  # 重置上下文
        else:
            # 增量翻译：添加之前的上下文
            text_to_translate = self.previous_context + new_text

            # 如果文本过长，截取最后的部分进行翻译
            if len(text_to_translate) > self.chunk_size + self.overlap:
                # 查找合适的截取点（句子边界或者空格）
                cutoff_point = self.chunk_size
                space_pos = text_to_translate.rfind(' ', 0, cutoff_point)
                if space_pos > cutoff_point - 20:  # 如果空格位置合理
                    cutoff_point = space_pos

                text_to_translate = text_to_translate[cutoff_point:]

            # 更新上下文
            self.previous_context = text_to_translate[-self.overlap:] if len(
                text_to_translate) > self.overlap else text_to_translate

        return text_to_translate

    def reset(self):
        """重置策略状态"""
        self.previous_context = ""
        self.translated_cache.clear()


class TranslationModule:
    """实时翻译模块"""

    def __init__(self,
                 translation_callback: Optional[Callable[[str, bool], None]] = None,
                 error_callback: Optional[Callable[[str], None]] = None):
        """
        初始化翻译模块

        Args:
            translation_callback: 翻译结果回调函数 (translated_text, is_final)
            error_callback: 错误回调函数
        """
        # 回调函数
        self.translation_callback = translation_callback
        self.error_callback = error_callback

        # 配置
        self.translation_config = config.translation

        # 模型和分词器
        self.model = None
        self.tokenizer = None
        self.current_model_name = None

        # SimulTrans策略
        self.simul_strategy = SimulTransStrategy(
            chunk_size=self.translation_config.chunk_size,
            overlap=32
        )

        # 翻译队列和线程
        self.translation_queue = queue.Queue()
        self.translation_thread = None
        self.running = False

        # 缓存和状态
        self.translation_cache = {}
        self.last_translated_text = ""

        # 性能统计
        self.translation_stats = {
            "total_translations": 0,
            "total_time": 0.0,
            "average_time": 0.0
        }

    def _report_error(self, error_msg: str):
        """报告错误"""
        print(f"[Translation Error]: {error_msg}")
        if self.error_callback:
            self.error_callback(error_msg)

    def _report_translation(self, translated_text: str, is_final: bool = False):
        """报告翻译结果"""
        if self.translation_callback:
            self.translation_callback(translated_text, is_final)

    async def initialize_model(self, source_lang: str = None, target_lang: str = None) -> bool:
        """
        初始化翻译模型

        Args:
            source_lang: 源语言代码
            target_lang: 目标语言代码
        """
        try:
            # 使用提供的语言或配置中的语言
            if source_lang and target_lang:
                config.update_language_pair(source_lang, target_lang)

            model_name = self.translation_config.model_name

            # 如果模型已经加载且是同一个模型，直接返回
            if self.model is not None and self.current_model_name == model_name:
                return True

            print(f"正在初始化翻译模型: {model_name}")
            print(f"翻译方向: {self.translation_config.source_language} -> {self.translation_config.target_language}")

            # 加载模型和分词器
            self.model, self.tokenizer = model_manager.load_translation_model(model_name)

            if self.model is None or self.tokenizer is None:
                raise Exception(f"翻译模型加载失败: {model_name}")

            self.current_model_name = model_name

            # 检测设备
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

            print(f"翻译模型初始化完成，使用设备: {self.device}")
            return True

        except Exception as e:
            self._report_error(f"翻译模型初始化失败: {e}")
            return False

    def _translate_text(self, text: str) -> Optional[str]:
        """
        执行文本翻译

        Args:
            text: 待翻译文本

        Returns:
            翻译结果，失败时返回None
        """
        if not text.strip():
            return ""

        # 检查缓存
        if text in self.translation_cache:
            return self.translation_cache[text]

        try:
            start_time = time.time()

            # 文本预处理
            text = text.strip()

            # 分词
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=self.translation_config.max_length,
                truncation=True,
                padding=True
            ).to(self.device)

            # 生成翻译
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=self.translation_config.max_length,
                    num_beams=self.translation_config.num_beams,
                    early_stopping=self.translation_config.early_stopping,
                    do_sample=False
                )

            # 解码结果
            translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # 后处理
            translated = self._post_process_translation(translated)

            # 缓存结果
            self.translation_cache[text] = translated

            # 更新统计
            translation_time = time.time() - start_time
            self.translation_stats["total_translations"] += 1
            self.translation_stats["total_time"] += translation_time
            self.translation_stats["average_time"] = (
                    self.translation_stats["total_time"] / self.translation_stats["total_translations"]
            )

            return translated

        except Exception as e:
            self._report_error(f"翻译过程错误: {e}")
            return None

    def _post_process_translation(self, translated_text: str) -> str:
        """后处理翻译结果"""
        # 基本清理
        translated_text = translated_text.strip()

        # 移除重复的标点符号
        translated_text = re.sub(r'([.!?]){2,}', r'\1', translated_text)

        # 确保句子以适当的标点结尾
        if translated_text and not re.search(r'[.!?。！？]$', translated_text):
            translated_text += '.'

        return translated_text

    def translation_worker(self):
        """翻译工作线程"""
        while self.running:
            try:
                # 获取翻译任务
                task = self.translation_queue.get(timeout=1.0)
                if task is None:  # 停止信号
                    break

                text, is_final = task

                # 使用SimulTrans策略准备文本
                text_to_translate = self.simul_strategy.prepare_text_for_translation(text, is_final)

                if text_to_translate is not None:
                    # 执行翻译
                    translated = self._translate_text(text_to_translate)

                    if translated is not None:
                        # 处理增量翻译结果
                        if not is_final and self.last_translated_text:
                            # 对于增量翻译，只返回新的部分
                            if translated.startswith(self.last_translated_text):
                                new_part = translated[len(self.last_translated_text):].strip()
                                if new_part:
                                    self._report_translation(new_part, is_final)
                            else:
                                # 如果不是增量，返回完整翻译
                                self._report_translation(translated, is_final)

                            if is_final:
                                self.last_translated_text = ""
                            else:
                                self.last_translated_text = translated
                        else:
                            # 首次翻译或最终翻译
                            self._report_translation(translated, is_final)
                            if is_final:
                                self.last_translated_text = ""
                            else:
                                self.last_translated_text = translated

                self.translation_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                self._report_error(f"翻译工作线程错误: {e}")

    def start_translation_service(self) -> bool:
        """启动翻译服务"""
        if self.running:
            return True

        if self.model is None:
            self._report_error("翻译模型未初始化")
            return False

        try:
            # 重置状态
            self.translation_queue = queue.Queue()
            self.simul_strategy.reset()
            self.last_translated_text = ""

            self.running = True

            # 启动翻译线程
            self.translation_thread = threading.Thread(target=self.translation_worker)
            self.translation_thread.daemon = True
            self.translation_thread.start()

            print("翻译服务已启动")
            return True

        except Exception as e:
            self._report_error(f"启动翻译服务失败: {e}")
            return False

    def stop_translation_service(self):
        """停止翻译服务"""
        print("正在停止翻译服务...")
        self.running = False

        # 发送停止信号
        if hasattr(self, 'translation_queue'):
            self.translation_queue.put(None)

        # 等待线程结束
        if self.translation_thread and self.translation_thread.is_alive():
            self.translation_thread.join(timeout=2)

        # 重置状态
        self.simul_strategy.reset()
        self.last_translated_text = ""

        print("翻译服务已停止")

    def add_translation_task(self, text: str, is_final: bool = False):
        """
        添加翻译任务

        Args:
            text: 待翻译文本
            is_final: 是否为最终文本
        """
        if self.running and text.strip():
            try:
                self.translation_queue.put((text, is_final), timeout=1.0)
            except queue.Full:
                self._report_error("翻译队列已满，丢弃翻译任务")

    def translate_immediate(self, text: str) -> Optional[str]:
        """
        立即翻译文本（同步方法）

        Args:
            text: 待翻译文本

        Returns:
            翻译结果
        """
        if self.model is None:
            self._report_error("翻译模型未初始化")
            return None

        return self._translate_text(text)

    def get_translation_stats(self) -> Dict[str, any]:
        """获取翻译统计信息"""
        return {
            **self.translation_stats,
            "cache_size": len(self.translation_cache),
            "queue_size": self.translation_queue.qsize() if hasattr(self, 'translation_queue') else 0,
            "is_running": self.running,
            "current_model": self.current_model_name,
            "language_pair": f"{self.translation_config.source_language}->{self.translation_config.target_language}"
        }

    def clear_cache(self):
        """清空翻译缓存"""
        self.translation_cache.clear()
        self.simul_strategy.reset()
        print("翻译缓存已清空")

    def change_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """
        更改翻译语言对

        Args:
            source_lang: 新的源语言
            target_lang: 新的目标语言

        Returns:
            是否成功更改
        """
        # 停止当前服务
        was_running = self.running
        if was_running:
            self.stop_translation_service()

        # 清空缓存
        self.clear_cache()

        # 重新初始化模型
        asyncio.create_task(self.initialize_model(source_lang, target_lang))

        # 如果之前在运行，重新启动
        if was_running:
            return self.start_translation_service()

        return True