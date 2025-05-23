"""
音频捕获与语音识别模块
==================
基于FunASR实现实时语音识别，支持VAD和标点恢复
"""

import sounddevice as sd
import numpy as np
import threading
import time
import queue
from typing import Callable, Optional
import asyncio

from config.settings import config
from models.model_manager import model_manager


class AudioCaptureModule:
    """音频捕获与语音识别模块"""

    def __init__(self,
                 text_callback: Optional[Callable[[str, bool], None]] = None,
                 error_callback: Optional[Callable[[str], None]] = None):
        """
        初始化音频捕获模块

        Args:
            text_callback: 文本识别回调函数 (text, is_final)
            error_callback: 错误回调函数
        """
        # 回调函数
        self.text_callback = text_callback
        self.error_callback = error_callback

        # 配置参数
        self.audio_config = config.audio
        self.model_config = config.model

        # 音频参数
        self.sample_rate = self.audio_config.sample_rate
        self.vad_chunk_samples = int(self.sample_rate * self.audio_config.vad_chunk_duration_ms / 1000)
        self.asr_chunk_samples = int(self.sample_rate * self.audio_config.chunk_duration_ms / 1000)

        # ASR参数
        self.asr_chunk_size = [0, 10, 5]  # 流式设置
        self.encoder_chunk_look_back = 4
        self.decoder_chunk_look_back = 1

        # 运行状态
        self.running = False
        self.is_speaking = False
        self.audio_queue = queue.Queue()
        self.speech_buffer = np.array([], dtype=np.float32)

        # 识别结果缓存
        self.current_sentence = ""
        self.complete_transcript = ""

        # 模型缓存
        self.asr_model = None
        self.vad_model = None
        self.punc_model = None
        self.vad_cache = {}
        self.asr_cache = {}

        # 时间追踪
        self.current_segment_start_time = None
        self.last_forced_segment_time = 0

        # 线程对象
        self.audio_thread = None
        self.stream = None

    def _report_error(self, error_msg: str):
        """报告错误"""
        print(f"[AudioCapture Error]: {error_msg}")
        if self.error_callback:
            self.error_callback(error_msg)

    def _report_text(self, text: str, is_final: bool = False):
        """报告识别文本"""
        if self.text_callback:
            self.text_callback(text, is_final)

    async def initialize_models(self) -> bool:
        """异步初始化所有需要的模型"""
        try:
            print("正在初始化语音识别模型...")

            # 加载ASR模型
            self.asr_model = model_manager.load_funasr_model(self.model_config.asr_model)
            if self.asr_model is None:
                raise Exception("ASR模型加载失败")

            # 加载VAD模型（如果启用）
            if self.audio_config.use_vad:
                self.vad_model = model_manager.load_funasr_model(self.model_config.vad_model)
                if self.vad_model is None:
                    print("VAD模型加载失败，将禁用VAD功能")
                    self.audio_config.use_vad = False

            # 加载标点模型（如果启用）
            if self.audio_config.use_punctuation:
                self.punc_model = model_manager.load_funasr_model(self.model_config.punc_model)
                if self.punc_model is None:
                    print("标点模型加载失败，将禁用标点功能")
                    self.audio_config.use_punctuation = False

            print("语音识别模型初始化完成")
            return True

        except Exception as e:
            self._report_error(f"模型初始化失败: {e}")
            return False

    def audio_callback(self, indata, frames, time, status):
        """音频流回调函数"""
        if status:
            print(f"Audio status: {status}")

        if self.running:
            self.audio_queue.put(indata.copy())

    def process_audio_thread(self):
        """音频处理线程"""
        vad_buffer = np.array([], dtype=np.float32)

        while self.running:
            try:
                audio_processed = False

                # 处理音频队列
                while not self.audio_queue.empty() and self.running:
                    chunk = self.audio_queue.get_nowait()
                    audio_processed = True

                    if self.audio_config.use_vad and self.vad_model is not None:
                        vad_buffer = np.append(vad_buffer, chunk.flatten())
                    else:
                        # 不使用VAD时直接添加到语音缓冲区
                        self.speech_buffer = np.append(self.speech_buffer, chunk.flatten())
                        if self.current_segment_start_time is None:
                            self.current_segment_start_time = time.time()

                # VAD处理
                if self.audio_config.use_vad and self.vad_model is not None:
                    while len(vad_buffer) >= self.vad_chunk_samples and self.running:
                        vad_chunk = vad_buffer[:self.vad_chunk_samples]
                        vad_buffer = vad_buffer[self.vad_chunk_samples:]
                        audio_processed = True

                        # VAD检测
                        vad_res = self.vad_model.generate(
                            input=vad_chunk,
                            cache=self.vad_cache,
                            is_final=False,
                            chunk_size=self.audio_config.vad_chunk_duration_ms
                        )

                        # 处理VAD结果
                        if len(vad_res[0]["value"]):
                            for segment_info in vad_res[0]["value"]:
                                if segment_info[0] != -1 and segment_info[1] == -1:
                                    # 语音开始
                                    if not self.is_speaking:
                                        self.is_speaking = True
                                        self.current_segment_start_time = time.time()
                                        print("\n[VAD] 检测到语音开始...")

                                elif segment_info[0] == -1 and segment_info[1] != -1:
                                    # 语音结束
                                    if self.is_speaking:
                                        self.is_speaking = False
                                        self.current_segment_start_time = None
                                        print("\n[VAD] 检测到语音结束...")
                                        if len(self.speech_buffer) > 0:
                                            self.process_asr_buffer(is_final=True)

                        # 如果正在说话，添加到语音缓冲区
                        if self.is_speaking:
                            self.speech_buffer = np.append(self.speech_buffer, vad_chunk)
                else:
                    # 不使用VAD时总是处于说话状态
                    if len(self.speech_buffer) > 0 and self.current_segment_start_time is None:
                        self.current_segment_start_time = time.time()
                    self.is_speaking = True

                # ASR处理
                if len(self.speech_buffer) >= self.asr_chunk_samples:
                    self.process_asr_buffer()
                    audio_processed = True

                # 检查最大片段时长
                if self.is_speaking and self.current_segment_start_time is not None:
                    current_time = time.time()
                    segment_duration = current_time - self.current_segment_start_time
                    time_since_last_force = current_time - self.last_forced_segment_time

                    if (segment_duration > self.audio_config.max_segment_duration_seconds and
                            time_since_last_force > self.audio_config.max_segment_duration_seconds / 2.0):

                        print(f"\n[Timeout] 片段超时 ({segment_duration:.2f}s)，强制分段...")
                        if len(self.speech_buffer) > 0:
                            self.process_asr_buffer(is_final=True)

                        self.current_segment_start_time = time.time()
                        self.last_forced_segment_time = current_time

                if not audio_processed:
                    time.sleep(0.01)

            except queue.Empty:
                if self.running:
                    time.sleep(0.01)
            except Exception as e:
                self._report_error(f"音频处理错误: {e}")
                if not self.running:
                    break
                time.sleep(0.1)

    def process_asr_buffer(self, is_final: bool = False):
        """处理ASR缓冲区"""
        if self.asr_model is None:
            return

        try:
            # 处理缓冲区为空但有待处理句子的情况
            if len(self.speech_buffer) == 0 and is_final:
                if self.current_sentence:
                    final_text = self.current_sentence
                    if self.audio_config.use_punctuation and self.punc_model is not None:
                        punc_res = self.punc_model.generate(input=self.current_sentence)
                        if punc_res and punc_res[0]["text"]:
                            final_text = punc_res[0]["text"]

                    self._report_text(final_text, True)
                    self.complete_transcript += final_text + " "
                    self.current_sentence = ""
                    self.asr_cache = {}
                return

            # 处理音频块
            if not is_final:
                if len(self.speech_buffer) < self.asr_chunk_samples:
                    return
                asr_chunk = self.speech_buffer[:self.asr_chunk_samples]
                self.speech_buffer = self.speech_buffer[self.asr_chunk_samples:]
            else:
                asr_chunk = self.speech_buffer
                self.speech_buffer = np.array([], dtype=np.float32)

            if len(asr_chunk) > 0:
                # ASR识别
                asr_res = self.asr_model.generate(
                    input=asr_chunk,
                    cache=self.asr_cache,
                    is_final=is_final,
                    chunk_size=self.asr_chunk_size,
                    encoder_chunk_look_back=self.encoder_chunk_look_back,
                    decoder_chunk_look_back=self.decoder_chunk_look_back
                )

                if asr_res and asr_res[0]["text"]:
                    segment_text = asr_res[0]["text"]

                    if self.audio_config.use_punctuation and self.punc_model is not None and is_final:
                        # 对完整句子应用标点
                        full_input = self.current_sentence + segment_text
                        punc_res = self.punc_model.generate(input=full_input)
                        if punc_res and punc_res[0]["text"]:
                            final_text = punc_res[0]["text"]
                        else:
                            final_text = full_input

                        self._report_text(final_text, True)
                        self.complete_transcript += final_text + " "
                        self.current_sentence = ""

                    elif not is_final:
                        # 累积当前句子并实时反馈
                        self.current_sentence += segment_text
                        self._report_text(self.current_sentence, False)

                    else:
                        # 最终处理但不使用标点
                        final_text = self.current_sentence + segment_text
                        self._report_text(final_text, True)
                        self.complete_transcript += final_text + " "
                        self.current_sentence = ""

            elif is_final and self.current_sentence:
                # 处理剩余的当前句子
                final_text = self.current_sentence
                if self.audio_config.use_punctuation and self.punc_model is not None:
                    punc_res = self.punc_model.generate(input=self.current_sentence)
                    if punc_res and punc_res[0]["text"]:
                        final_text = punc_res[0]["text"]

                self._report_text(final_text, True)
                self.complete_transcript += final_text + " "
                self.current_sentence = ""

            if is_final:
                self.asr_cache = {}

        except Exception as e:
            self._report_error(f"ASR处理错误: {e}")

    def start_capture(self) -> bool:
        """开始音频捕获"""
        if self.running:
            return True

        try:
            # 重置状态
            self.audio_queue = queue.Queue()
            self.speech_buffer = np.array([], dtype=np.float32)
            self.vad_cache = {}
            self.asr_cache = {}
            self.current_sentence = ""
            self.complete_transcript = ""
            self.is_speaking = False if self.audio_config.use_vad else True
            self.current_segment_start_time = None if self.audio_config.use_vad else time.time()
            self.last_forced_segment_time = time.time()

            self.running = True

            # 启动音频处理线程
            self.audio_thread = threading.Thread(target=self.process_audio_thread)
            self.audio_thread.daemon = True
            self.audio_thread.start()

            # 启动音频流
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=self.audio_config.channels,
                samplerate=self.sample_rate,
                dtype='float32'
            )
            self.stream.start()

            print("音频捕获已启动")
            return True

        except Exception as e:
            self._report_error(f"启动音频捕获失败: {e}")
            self.running = False
            return False

    def stop_capture(self):
        """停止音频捕获"""
        print("正在停止音频捕获...")
        self.running = False

        # 停止音频流
        if self.stream:
            try:
                if not self.stream.stopped:
                    self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"关闭音频流错误: {e}")
            self.stream = None

        # 等待处理线程结束
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2)

        # 处理剩余数据
        if len(self.speech_buffer) > 0 or self.current_sentence:
            self.process_asr_buffer(is_final=True)

        # 清理缓存
        self.vad_cache = {}
        self.asr_cache = {}

        print("音频捕获已停止")

    def get_transcript(self) -> str:
        """获取完整的转录文本"""
        return self.complete_transcript.strip()

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running