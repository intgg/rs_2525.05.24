"""
配置管理模块
===========
统一管理系统配置参数，支持多语言翻译对配置
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 600
    vad_chunk_duration_ms: int = 200
    max_segment_duration_seconds: float = 7.0
    use_vad: bool = True
    use_punctuation: bool = True


@dataclass
class TranslationConfig:
    """翻译配置"""
    source_language: str = "zh"  # 源语言
    target_language: str = "en"  # 目标语言
    model_name: str = "Helsinki-NLP/opus-mt-zh-en"  # 默认中英翻译模型
    max_length: int = 512
    num_beams: int = 4
    early_stopping: bool = True
    chunk_size: int = 128  # SimulTrans策略的块大小


@dataclass
class TTSConfig:
    """语音合成配置"""
    voice: str = "en-US-AriaNeural"  # 默认英语音色
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"


@dataclass
class ModelConfig:
    """模型配置"""
    models_dir: str = "./models/cached_models"
    asr_model: str = "paraformer-zh-streaming"
    vad_model: str = "fsmn-vad"
    punc_model: str = "ct-punc"
    translation_models: Dict[str, str] = None

    def __post_init__(self):
        if self.translation_models is None:
            self.translation_models = {
                "zh-en": "Helsinki-NLP/opus-mt-zh-en",
                "en-zh": "Helsinki-NLP/opus-mt-en-zh",
                "zh-ja": "Helsinki-NLP/opus-mt-zh-ja",
                "ja-zh": "Helsinki-NLP/opus-mt-ja-zh",
                "en-ja": "Helsinki-NLP/opus-mt-en-ja",
                "ja-en": "Helsinki-NLP/opus-mt-ja-en",
                "zh-ko": "Helsinki-NLP/opus-mt-zh-ko",
                "ko-zh": "Helsinki-NLP/opus-mt-ko-zh",
            }


class SystemConfig:
    """系统配置管理器"""

    def __init__(self):
        self.audio = AudioConfig()
        self.translation = TranslationConfig()
        self.tts = TTSConfig()
        self.model = ModelConfig()

        # 语言对应的TTS音色映射
        self.tts_voices = {
            "en": "en-US-AriaNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
            "ja": "ja-JP-NanamiNeural",
            "ko": "ko-KR-SunHiNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "es": "es-ES-ElviraNeural",
            "ru": "ru-RU-SvetlanaNeural",
        }

        # 确保模型目录存在
        os.makedirs(self.model.models_dir, exist_ok=True)

    def get_translation_model(self, source_lang: str, target_lang: str) -> str:
        """获取指定语言对的翻译模型"""
        lang_pair = f"{source_lang}-{target_lang}"
        return self.model.translation_models.get(lang_pair,
                                                 f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}")

    def get_tts_voice(self, language: str) -> str:
        """获取指定语言的TTS音色"""
        return self.tts_voices.get(language, "en-US-AriaNeural")

    def update_language_pair(self, source_lang: str, target_lang: str):
        """更新翻译语言对"""
        self.translation.source_language = source_lang
        self.translation.target_language = target_lang
        self.translation.model_name = self.get_translation_model(source_lang, target_lang)
        self.tts.voice = self.get_tts_voice(target_lang)

    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        languages = set()
        for lang_pair in self.model.translation_models.keys():
            source, target = lang_pair.split("-")
            languages.add(source)
            languages.add(target)
        return sorted(list(languages))


# 全局配置实例
config = SystemConfig()


def load_config_from_file(config_file: str = "config.yaml") -> SystemConfig:
    """从配置文件加载配置（可选功能）"""
    # 这里可以实现从YAML或JSON文件加载配置
    # 暂时返回默认配置
    return config


def save_config_to_file(config_obj: SystemConfig, config_file: str = "config.yaml"):
    """保存配置到文件（可选功能）"""
    # 这里可以实现保存配置到YAML或JSON文件
    pass