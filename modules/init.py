"""
核心功能模块
===========
包含音频捕获、翻译、语音合成和管道协调等核心功能
"""

from .audio_capture import AudioCaptureModule
from .translator import TranslationModule
from .text_to_speech import TextToSpeechModule
from .pipeline import RealTimeTranslationPipeline

__all__ = [
    'AudioCaptureModule',
    'TranslationModule',
    'TextToSpeechModule',
    'RealTimeTranslationPipeline'
]