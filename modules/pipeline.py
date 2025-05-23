"""
系统管道协调器
=============
整合音频捕获、翻译和语音合成模块，实现端到端的实时语音翻译
"""

import asyncio
import time
import threading
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass

from config.settings import config
from modules.audio_capture import AudioCaptureModule
from modules.translator import TranslationModule
from modules.text_to_speech import TextToSpeechModule


@dataclass
class TranslationSession:
    """翻译会话信息"""
    session_id: str
    source_language: str
    target_language: str
    start_time: float
    total_audio_time: float = 0.0
    total_text_length: int = 0
    total_translations: int = 0


class RealTimeTranslationPipeline:
    """实时语音翻译管道"""

    def __init__(self):
        """初始化翻译管道"""
        # 状态管理
        self.is_initialized = False
        self.is_running = False
        self.current_session: Optional[TranslationSession] = None

        # 模块实例
        self.audio_module = None
        self.translation_module = None
        self.tts_module = None

        # 回调函数
        self.status_callbacks = []
        self.text_callbacks = []
        self.translation_callbacks = []
        self.error_callbacks = []

        # 性能监控
        self.performance_stats = {
            "sessions_count": 0,
            "total_runtime": 0.0,
            "average_latency": 0.0,
            "error_count": 0
        }

        # 缓存最近的文本，用于上下文处理
        self.recent_source_texts = []
        self.recent_translations = []
        self.max_context_items = 5

    def add_status_callback(self, callback: Callable[[str, Dict], None]):
        """添加状态回调函数"""
        self.status_callbacks.append(callback)

    def add_text_callback(self, callback: Callable[[str, bool], None]):
        """添加识别文本回调函数"""
        self.text_callbacks.append(callback)

    def add_translation_callback(self, callback: Callable[[str, bool], None]):
        """添加翻译结果回调函数"""
        self.translation_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[str], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)

    def _report_status(self, status: str, data: Dict = None):
        """报告系统状态"""
        if data is None:
            data = {}

        print(f"[Pipeline Status]: {status}")
        for callback in self.status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                print(f"状态回调错误: {e}")

    def _report_error(self, error_msg: str):
        """报告错误"""
        print(f"[Pipeline Error]: {error_msg}")
        self.performance_stats["error_count"] += 1

        for callback in self.error_callbacks:
            try:
                callback(error_msg)
            except Exception as e:
                print(f"错误回调执行失败: {e}")

    def _on_text_recognized(self, text: str, is_final: bool):
        """处理语音识别结果"""
        try:
            # 更新会话统计
            if self.current_session:
                self.current_session.total_text_length += len(text)

            # 缓存识别文本
            if is_final and text.strip():
                self.recent_source_texts.append(text.strip())
                if len(self.recent_source_texts) > self.max_context_items:
                    self.recent_source_texts.pop(0)

            # 通知文本回调
            for callback in self.text_callbacks:
                try:
                    callback(text, is_final)
                except Exception as e:
                    print(f"文本回调错误: {e}")

            # 发送给翻译模块
            if self.translation_module and text.strip():
                self.translation_module.add_translation_task(text, is_final)

        except Exception as e:
            self._report_error(f"文本识别处理错误: {e}")

    def _on_translation_result(self, translated_text: str, is_final: bool):
        """处理翻译结果"""
        try:
            # 更新会话统计
            if self.current_session and is_final:
                self.current_session.total_translations += 1

            # 缓存翻译结果
            if is_final and translated_text.strip():
                self.recent_translations.append(translated_text.strip())
                if len(self.recent_translations) > self.max_context_items:
                    self.recent_translations.pop(0)

            # 通知翻译回调
            for callback in self.translation_callbacks:
                try:
                    callback(translated_text, is_final)
                except Exception as e:
                    print(f"翻译回调错误: {e}")

            # 发送给TTS模块（只有最终结果才播放）
            if self.tts_module and is_final and translated_text.strip():
                self.tts_module.speak(translated_text, priority="normal")

        except Exception as e:
            self._report_error(f"翻译结果处理错误: {e}")

    def _on_audio_error(self, error_msg: str):
        """处理音频模块错误"""
        self._report_error(f"音频模块错误: {error_msg}")

    def _on_translation_error(self, error_msg: str):
        """处理翻译模块错误"""
        self._report_error(f"翻译模块错误: {error_msg}")

    def _on_tts_error(self, error_msg: str):
        """处理TTS模块错误"""
        self._report_error(f"TTS模块错误: {error_msg}")

    def _on_tts_playback(self, text: str, is_playing: bool):
        """处理TTS播放状态"""
        status = "playing" if is_playing else "finished"
        self._report_status(f"TTS {status}", {"text": text[:50] + "..." if len(text) > 50 else text})

    async def initialize(self, source_lang: str = "zh", target_lang: str = "en") -> bool:
        """
        初始化翻译管道

        Args:
            source_lang: 源语言代码
            target_lang: 目标语言代码

        Returns:
            是否初始化成功
        """
        try:
            self._report_status("正在初始化翻译管道...")

            # 更新语言配置
            config.update_language_pair(source_lang, target_lang)

            # 初始化音频捕获模块
            self._report_status("初始化音频捕获模块...")
            self.audio_module = AudioCaptureModule(
                text_callback=self._on_text_recognized,
                error_callback=self._on_audio_error
            )

            if not await self.audio_module.initialize_models():
                raise Exception("音频模块初始化失败")

            # 初始化翻译模块
            self._report_status("初始化翻译模块...")
            self.translation_module = TranslationModule(
                translation_callback=self._on_translation_result,
                error_callback=self._on_translation_error
            )

            if not await self.translation_module.initialize_model(source_lang, target_lang):
                raise Exception("翻译模块初始化失败")

            # 初始化TTS模块
            self._report_status("初始化TTS模块...")
            self.tts_module = TextToSpeechModule(
                playback_callback=self._on_tts_playback,
                error_callback=self._on_tts_error
            )

            # 加载TTS音色
            await self.tts_module.load_available_voices()
            self.tts_module.set_voice_for_language(target_lang)

            self.is_initialized = True
            self._report_status("翻译管道初始化完成", {
                "source_language": source_lang,
                "target_language": target_lang,
                "tts_voice": self.tts_module.current_voice
            })

            return True

        except Exception as e:
            self._report_error(f"初始化失败: {e}")
            return False

    def start_translation(self) -> bool:
        """启动翻译服务"""
        if not self.is_initialized:
            self._report_error("管道未初始化，请先调用 initialize()")
            return False

        if self.is_running:
            self._report_status("翻译服务已在运行中")
            return True

        try:
            self._report_status("启动翻译服务...")

            # 创建新的翻译会话
            session_id = f"session_{int(time.time())}"
            self.current_session = TranslationSession(
                session_id=session_id,
                source_language=config.translation.source_language,
                target_language=config.translation.target_language,
                start_time=time.time()
            )

            # 启动各个模块
            if not self.translation_module.start_translation_service():
                raise Exception("翻译服务启动失败")

            if not self.tts_module.start_tts_service():
                raise Exception("TTS服务启动失败")

            if not self.audio_module.start_capture():
                raise Exception("音频捕获启动失败")

            self.is_running = True
            self.performance_stats["sessions_count"] += 1

            self._report_status("翻译服务已启动", {
                "session_id": session_id,
                "source_language": self.current_session.source_language,
                "target_language": self.current_session.target_language
            })

            return True

        except Exception as e:
            self._report_error(f"启动翻译服务失败: {e}")
            self.stop_translation()
            return False

    def stop_translation(self):
        """停止翻译服务"""
        if not self.is_running:
            return

        try:
            self._report_status("正在停止翻译服务...")

            # 停止各个模块
            if self.audio_module:
                self.audio_module.stop_capture()

            if self.translation_module:
                self.translation_module.stop_translation_service()

            if self.tts_module:
                self.tts_module.stop_tts_service()

            # 更新会话统计
            if self.current_session:
                session_duration = time.time() - self.current_session.start_time
                self.performance_stats["total_runtime"] += session_duration
                self.current_session = None

            self.is_running = False
            self._report_status("翻译服务已停止")

        except Exception as e:
            self._report_error(f"停止翻译服务时出错: {e}")

    def change_language_pair(self, source_lang: str, target_lang: str) -> bool:
        """
        更改翻译语言对

        Args:
            source_lang: 新的源语言
            target_lang: 新的目标语言

        Returns:
            是否更改成功
        """
        try:
            self._report_status(f"更改语言对: {source_lang} -> {target_lang}")

            # 如果正在运行，先停止
            was_running = self.is_running
            if was_running:
                self.stop_translation()

            # 更新配置
            config.update_language_pair(source_lang, target_lang)

            # 重新初始化翻译模块
            if self.translation_module:
                success = self.translation_module.change_language_pair(source_lang, target_lang)
                if not success:
                    raise Exception("翻译模块语言切换失败")

            # 更新TTS音色
            if self.tts_module:
                self.tts_module.set_voice_for_language(target_lang)

            # 如果之前在运行，重新启动
            if was_running:
                return self.start_translation()

            self._report_status("语言对更改成功", {
                "source_language": source_lang,
                "target_language": target_lang
            })

            return True

        except Exception as e:
            self._report_error(f"更改语言对失败: {e}")
            return False

    def set_tts_voice(self, voice_name: str):
        """设置TTS音色"""
        if self.tts_module:
            self.tts_module.set_voice(voice_name)
            self._report_status(f"TTS音色已更改: {voice_name}")

    def get_available_voices(self, language_code: str = None) -> Dict:
        """获取可用的TTS音色"""
        if self.tts_module:
            return self.tts_module.list_available_voices(language_code)
        return {}

    def get_pipeline_status(self) -> Dict:
        """获取管道状态信息"""
        status = {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "current_session": None,
            "performance_stats": self.performance_stats.copy(),
            "module_status": {}
        }

        if self.current_session:
            status["current_session"] = {
                "session_id": self.current_session.session_id,
                "source_language": self.current_session.source_language,
                "target_language": self.current_session.target_language,
                "runtime": time.time() - self.current_session.start_time,
                "total_text_length": self.current_session.total_text_length,
                "total_translations": self.current_session.total_translations
            }

        # 收集模块状态
        if self.audio_module:
            status["module_status"]["audio"] = {
                "is_running": self.audio_module.is_running(),
                "transcript_length": len(self.audio_module.get_transcript())
            }

        if self.translation_module:
            status["module_status"]["translation"] = self.translation_module.get_translation_stats()

        if self.tts_module:
            status["module_status"]["tts"] = self.tts_module.get_tts_stats()

        return status

    def get_recent_context(self) -> Dict[str, List[str]]:
        """获取最近的翻译上下文"""
        return {
            "source_texts": self.recent_source_texts.copy(),
            "translations": self.recent_translations.copy()
        }

    def clear_context(self):
        """清空翻译上下文"""
        self.recent_source_texts.clear()
        self.recent_translations.clear()
        self._report_status("翻译上下文已清空")

    def emergency_stop(self):
        """紧急停止所有服务"""
        self._report_status("执行紧急停止...")

        try:
            # 强制停止所有模块
            if self.tts_module:
                self.tts_module.stop_current_playback()
                self.tts_module.running = False

            if self.translation_module:
                self.translation_module.running = False

            if self.audio_module:
                self.audio_module.running = False

            self.is_running = False
            self._report_status("紧急停止完成")

        except Exception as e:
            print(f"紧急停止时出错: {e}")

    def __del__(self):
        """析构函数，确保资源正确释放"""
        if self.is_running:
            self.stop_translation()