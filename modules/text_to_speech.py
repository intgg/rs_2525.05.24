"""
语音合成模块
===========
基于Edge TTS实现实时文本转语音功能
"""

import asyncio
import io
import threading
import queue
import time
from typing import Optional, Callable, Dict, List
import pygame
from pygame import mixer

try:
    import edge_tts
except ImportError as e:
    print(f"TTS依赖库未安装: {e}")
    print("请运行: pip install edge-tts pygame")

from config.settings import config


class TextToSpeechModule:
    """文本转语音模块"""

    def __init__(self,
                 playback_callback: Optional[Callable[[str, bool], None]] = None,
                 error_callback: Optional[Callable[[str], None]] = None):
        """
        初始化TTS模块

        Args:
            playback_callback: 播放状态回调函数 (text, is_playing)
            error_callback: 错误回调函数
        """
        # 回调函数
        self.playback_callback = playback_callback
        self.error_callback = error_callback

        # 配置
        self.tts_config = config.tts

        # 播放相关
        self.is_mixer_initialized = False
        self.current_voice = self.tts_config.voice

        # 异步TTS队列和线程
        self.tts_queue = queue.Queue()
        self.tts_thread = None
        self.running = False

        # 音频播放队列
        self.audio_queue = queue.Queue()
        self.playback_thread = None

        # 状态管理
        self.is_playing = False
        self.current_text = ""

        # 可用音色缓存
        self.available_voices = {}
        self.voices_loaded = False

        # 性能统计
        self.tts_stats = {
            "total_synthesis": 0,
            "total_synthesis_time": 0.0,
            "total_playback_time": 0.0,
            "average_synthesis_time": 0.0
        }

    def _report_error(self, error_msg: str):
        """报告错误"""
        print(f"[TTS Error]: {error_msg}")
        if self.error_callback:
            self.error_callback(error_msg)

    def _report_playback_status(self, text: str, is_playing: bool):
        """报告播放状态"""
        if self.playback_callback:
            self.playback_callback(text, is_playing)

    def _initialize_mixer(self):
        """初始化pygame混音器"""
        if not self.is_mixer_initialized:
            try:
                mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.is_mixer_initialized = True
                print("音频混音器初始化完成")
            except Exception as e:
                self._report_error(f"音频混音器初始化失败: {e}")
                return False
        return True

    async def load_available_voices(self):
        """加载可用的语音列表"""
        if self.voices_loaded:
            return

        try:
            print("正在加载可用语音列表...")
            voices_manager = await edge_tts.VoicesManager.create()

            # 按语言分组整理音色
            for voice in voices_manager.voices:
                lang_code = voice["Locale"]
                if lang_code not in self.available_voices:
                    self.available_voices[lang_code] = []

                self.available_voices[lang_code].append({
                    "name": voice["ShortName"],
                    "gender": voice["Gender"],
                    "friendly_name": voice.get("FriendlyName", ""),
                    "locale": lang_code
                })

            self.voices_loaded = True
            print(f"加载了 {len(self.available_voices)} 种语言的音色")

        except Exception as e:
            self._report_error(f"加载语音列表失败: {e}")

    def get_voices_for_language(self, language_code: str) -> List[Dict]:
        """获取指定语言的可用音色"""
        return self.available_voices.get(language_code, [])

    def get_best_voice_for_language(self, language_code: str, gender: str = "Female") -> str:
        """为指定语言获取最佳音色"""
        voices = self.get_voices_for_language(language_code)
        if not voices:
            # 如果没有找到指定语言的音色，返回默认音色
            return config.get_tts_voice(language_code)

        # 优先选择指定性别的音色
        preferred_voices = [v for v in voices if v["gender"] == gender]
        if preferred_voices:
            return preferred_voices[0]["name"]

        # 如果没有指定性别的音色，返回第一个可用的
        return voices[0]["name"]

    async def _synthesize_speech(self, text: str, voice: str = None) -> Optional[bytes]:
        """
        异步合成语音

        Args:
            text: 待合成的文本
            voice: 使用的音色，如果为None则使用当前配置的音色

        Returns:
            音频数据的字节流，失败时返回None
        """
        if not text.strip():
            return None

        try:
            start_time = time.time()

            # 使用指定音色或当前配置的音色
            voice_to_use = voice or self.current_voice

            # 创建TTS通信对象
            communicate = edge_tts.Communicate(text, voice_to_use)

            # 收集音频数据
            audio_data = bytes()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if not audio_data:
                self._report_error(f"未生成音频数据: {text[:50]}...")
                return None

            # 更新统计
            synthesis_time = time.time() - start_time
            self.tts_stats["total_synthesis"] += 1
            self.tts_stats["total_synthesis_time"] += synthesis_time
            self.tts_stats["average_synthesis_time"] = (
                    self.tts_stats["total_synthesis_time"] / self.tts_stats["total_synthesis"]
            )

            return audio_data

        except edge_tts.exceptions.NoAudioReceived:
            self._report_error(f"未收到音频数据，可能是网络问题或音色不支持该文本: {text[:50]}...")
            return None
        except Exception as e:
            self._report_error(f"语音合成错误: {e}")
            return None

    async def _play_audio_from_memory(self, audio_data: bytes, text: str):
        """从内存播放音频数据"""
        if not self._initialize_mixer():
            return

        try:
            start_time = time.time()

            # 创建内存缓冲区
            audio_io = io.BytesIO(audio_data)

            # 标记播放开始
            self.is_playing = True
            self.current_text = text
            self._report_playback_status(text, True)

            # 加载并播放音频
            mixer.music.load(audio_io)
            mixer.music.play()

            # 等待播放完成
            while mixer.music.get_busy():
                await asyncio.sleep(0.1)

            # 卸载音频资源
            mixer.music.unload()

            # 更新统计
            playback_time = time.time() - start_time
            self.tts_stats["total_playback_time"] += playback_time

            # 标记播放结束
            self.is_playing = False
            self.current_text = ""
            self._report_playback_status(text, False)

        except Exception as e:
            self._report_error(f"音频播放错误: {e}")
            self.is_playing = False
            self.current_text = ""
            self._report_playback_status(text, False)

    def tts_worker(self):
        """TTS工作线程"""
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while self.running:
                try:
                    # 获取TTS任务
                    task = self.tts_queue.get(timeout=1.0)
                    if task is None:  # 停止信号
                        break

                    text, voice, priority = task

                    # 如果是高优先级任务且正在播放，停止当前播放
                    if priority == "high" and self.is_playing:
                        self.stop_current_playback()

                    # 异步合成语音
                    audio_data = loop.run_until_complete(
                        self._synthesize_speech(text, voice)
                    )

                    if audio_data:
                        # 异步播放音频
                        loop.run_until_complete(
                            self._play_audio_from_memory(audio_data, text)
                        )

                    self.tts_queue.task_done()

                except queue.Empty:
                    continue
                except Exception as e:
                    self._report_error(f"TTS工作线程错误: {e}")
        finally:
            loop.close()

    def start_tts_service(self) -> bool:
        """启动TTS服务"""
        if self.running:
            return True

        try:
            # 初始化混音器
            if not self._initialize_mixer():
                return False

            # 重置状态
            self.tts_queue = queue.Queue()
            self.is_playing = False
            self.current_text = ""

            self.running = True

            # 启动TTS工作线程
            self.tts_thread = threading.Thread(target=self.tts_worker)
            self.tts_thread.daemon = True
            self.tts_thread.start()

            print("TTS服务已启动")
            return True

        except Exception as e:
            self._report_error(f"启动TTS服务失败: {e}")
            return False

    def stop_tts_service(self):
        """停止TTS服务"""
        print("正在停止TTS服务...")
        self.running = False

        # 停止当前播放
        self.stop_current_playback()

        # 发送停止信号
        if hasattr(self, 'tts_queue'):
            self.tts_queue.put(None)

        # 等待线程结束
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=3)

        # 重置状态
        self.is_playing = False
        self.current_text = ""

        print("TTS服务已停止")

    def speak(self, text: str, voice: str = None, priority: str = "normal"):
        """
        添加语音合成任务

        Args:
            text: 待合成的文本
            voice: 使用的音色（可选）
            priority: 任务优先级 ("normal" 或 "high")
        """
        if not self.running:
            self._report_error("TTS服务未启动")
            return

        if not text.strip():
            return

        try:
            self.tts_queue.put((text, voice, priority), timeout=1.0)
        except queue.Full:
            self._report_error("TTS队列已满，丢弃语音任务")

    def speak_immediate(self, text: str, voice: str = None) -> bool:
        """
        立即合成并播放语音（同步方法）

        Args:
            text: 待合成的文本
            voice: 使用的音色（可选）

        Returns:
            是否成功
        """
        if not text.strip():
            return False

        try:
            # 停止当前播放
            self.stop_current_playback()

            # 创建临时事件循环进行同步调用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 合成语音
                audio_data = loop.run_until_complete(
                    self._synthesize_speech(text, voice)
                )

                if audio_data:
                    # 播放音频
                    loop.run_until_complete(
                        self._play_audio_from_memory(audio_data, text)
                    )
                    return True
                else:
                    return False
            finally:
                loop.close()

        except Exception as e:
            self._report_error(f"立即语音合成失败: {e}")
            return False

    def stop_current_playback(self):
        """停止当前播放"""
        if self.is_playing:
            try:
                mixer.music.stop()
                self.is_playing = False
                if self.current_text:
                    self._report_playback_status(self.current_text, False)
                self.current_text = ""
            except:
                pass

    def set_voice(self, voice: str):
        """设置当前使用的音色"""
        self.current_voice = voice
        self.tts_config.voice = voice
        print(f"已切换到音色: {voice}")

    def set_voice_for_language(self, language_code: str, gender: str = "Female"):
        """为指定语言设置最佳音色"""
        if not self.voices_loaded:
            asyncio.run(self.load_available_voices())

        best_voice = self.get_best_voice_for_language(language_code, gender)
        self.set_voice(best_voice)
        return best_voice

    def get_tts_stats(self) -> Dict[str, any]:
        """获取TTS统计信息"""
        return {
            **self.tts_stats,
            "queue_size": self.tts_queue.qsize() if hasattr(self, 'tts_queue') else 0,
            "is_playing": self.is_playing,
            "current_voice": self.current_voice,
            "current_text": self.current_text,
            "is_running": self.running,
            "available_languages": len(self.available_voices)
        }

    def list_available_voices(self, language_code: str = None) -> Dict[str, List]:
        """列出可用的音色"""
        if not self.voices_loaded:
            asyncio.run(self.load_available_voices())

        if language_code:
            return {language_code: self.available_voices.get(language_code, [])}
        else:
            return self.available_voices

    def is_currently_playing(self) -> bool:
        """检查是否正在播放"""
        return self.is_playing