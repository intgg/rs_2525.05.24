"""
模型管理模块
===========
负责自动下载、缓存和管理所有AI模型
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Callable
import threading
import time

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
    from funasr import AutoModel
except ImportError as e:
    print(f"模型依赖库未安装: {e}")
    print("请运行: pip install transformers torch funasr")


class ModelManager:
    """模型管理器 - 统一管理所有AI模型的下载、缓存和加载"""

    def __init__(self, models_dir: str = "./models/cached_models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 模型缓存
        self._model_cache: Dict[str, any] = {}
        self._tokenizer_cache: Dict[str, any] = {}

        # 下载进度回调
        self._progress_callback: Optional[Callable] = None

        # 模型状态文件
        self.status_file = self.models_dir / "model_status.json"
        self._load_model_status()

        # 线程锁
        self._lock = threading.Lock()

    def _load_model_status(self):
        """加载模型状态信息"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    self.model_status = json.load(f)
            except:
                self.model_status = {}
        else:
            self.model_status = {}

    def _save_model_status(self):
        """保存模型状态信息"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(self.model_status, f, indent=2, ensure_ascii=False)

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """设置下载进度回调函数"""
        self._progress_callback = callback

    def _report_progress(self, model_name: str, progress: float):
        """报告下载进度"""
        if self._progress_callback:
            self._progress_callback(model_name, progress)

    def is_model_downloaded(self, model_name: str, model_type: str = "transformers") -> bool:
        """检查模型是否已下载"""
        model_key = f"{model_type}:{model_name}"
        return model_key in self.model_status and self.model_status[model_key].get("downloaded", False)

    def download_funasr_model(self, model_name: str) -> bool:
        """下载FunASR模型"""
        try:
            print(f"正在下载FunASR模型: {model_name}")
            self._report_progress(model_name, 0.0)

            # FunASR模型会自动下载到用户目录，我们这里主要是触发下载
            model = AutoModel(model=model_name)

            # 标记为已下载
            model_key = f"funasr:{model_name}"
            self.model_status[model_key] = {
                "downloaded": True,
                "download_time": time.time(),
                "model_type": "funasr"
            }
            self._save_model_status()

            self._report_progress(model_name, 1.0)
            print(f"FunASR模型 {model_name} 下载完成")
            return True

        except Exception as e:
            print(f"下载FunASR模型 {model_name} 失败: {e}")
            return False

    def download_translation_model(self, model_name: str) -> bool:
        """下载翻译模型"""
        try:
            print(f"正在下载翻译模型: {model_name}")
            self._report_progress(model_name, 0.0)

            # 设置本地缓存目录
            local_model_dir = self.models_dir / "transformers" / model_name.replace("/", "--")

            # 下载tokenizer
            print(f"下载tokenizer...")
            self._report_progress(model_name, 0.3)
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=str(local_model_dir),
                local_files_only=False
            )

            # 下载模型
            print(f"下载模型权重...")
            self._report_progress(model_name, 0.7)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                cache_dir=str(local_model_dir),
                local_files_only=False
            )

            # 标记为已下载
            model_key = f"transformers:{model_name}"
            self.model_status[model_key] = {
                "downloaded": True,
                "download_time": time.time(),
                "model_type": "transformers",
                "local_path": str(local_model_dir)
            }
            self._save_model_status()

            self._report_progress(model_name, 1.0)
            print(f"翻译模型 {model_name} 下载完成")
            return True

        except Exception as e:
            print(f"下载翻译模型 {model_name} 失败: {e}")
            return False

    def load_funasr_model(self, model_name: str, force_reload: bool = False):
        """加载FunASR模型"""
        with self._lock:
            cache_key = f"funasr:{model_name}"

            if not force_reload and cache_key in self._model_cache:
                return self._model_cache[cache_key]

            try:
                # 如果模型未下载，先下载
                if not self.is_model_downloaded(model_name, "funasr"):
                    if not self.download_funasr_model(model_name):
                        raise Exception(f"无法下载模型 {model_name}")

                print(f"加载FunASR模型: {model_name}")

                # 禁用FunASR的自动更新检查以加速加载
                os.environ["FUNASR_DISABLE_UPDATE"] = "True"

                model = AutoModel(model=model_name)
                self._model_cache[cache_key] = model

                print(f"FunASR模型 {model_name} 加载完成")
                return model

            except Exception as e:
                print(f"加载FunASR模型 {model_name} 失败: {e}")
                return None

    def load_translation_model(self, model_name: str, force_reload: bool = False):
        """加载翻译模型"""
        with self._lock:
            cache_key = f"transformers:{model_name}"
            tokenizer_key = f"tokenizer:{model_name}"

            if not force_reload and cache_key in self._model_cache:
                return self._model_cache[cache_key], self._tokenizer_cache[tokenizer_key]

            try:
                # 如果模型未下载，先下载
                if not self.is_model_downloaded(model_name, "transformers"):
                    if not self.download_translation_model(model_name):
                        raise Exception(f"无法下载模型 {model_name}")

                print(f"加载翻译模型: {model_name}")

                # 获取本地模型路径
                local_model_dir = self.models_dir / "transformers" / model_name.replace("/", "--")

                # 首先尝试从本地加载，如果失败则从HuggingFace加载
                try:
                    tokenizer = AutoTokenizer.from_pretrained(str(local_model_dir), local_files_only=True)
                    model = AutoModelForSeq2SeqLM.from_pretrained(str(local_model_dir), local_files_only=True)
                except:
                    print(f"本地模型加载失败，从HuggingFace加载...")
                    tokenizer = AutoTokenizer.from_pretrained(model_name)
                    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

                self._model_cache[cache_key] = model
                self._tokenizer_cache[tokenizer_key] = tokenizer

                print(f"翻译模型 {model_name} 加载完成")
                return model, tokenizer

            except Exception as e:
                print(f"加载翻译模型 {model_name} 失败: {e}")
                return None, None

    def preload_models(self, models_config: Dict[str, str], progress_callback: Optional[Callable] = None):
        """预加载指定的模型"""
        if progress_callback:
            self.set_progress_callback(progress_callback)

        total_models = len(models_config)
        loaded_count = 0

        for model_type, model_name in models_config.items():
            try:
                print(f"预加载模型 ({loaded_count + 1}/{total_models}): {model_name}")

                if model_type in ["asr", "vad", "punc"]:
                    self.load_funasr_model(model_name)
                elif model_type == "translation":
                    self.load_translation_model(model_name)

                loaded_count += 1
                if progress_callback:
                    progress_callback(f"预加载进度", loaded_count / total_models)

            except Exception as e:
                print(f"预加载模型 {model_name} 失败: {e}")

        print(f"模型预加载完成: {loaded_count}/{total_models}")

    def clear_cache(self):
        """清空模型缓存"""
        with self._lock:
            self._model_cache.clear()
            self._tokenizer_cache.clear()
            print("模型缓存已清空")

    def get_model_info(self) -> Dict[str, any]:
        """获取模型信息"""
        return {
            "cached_models": len(self._model_cache),
            "cached_tokenizers": len(self._tokenizer_cache),
            "downloaded_models": len(self.model_status),
            "models_dir": str(self.models_dir),
            "model_status": self.model_status
        }


# 全局模型管理器实例
model_manager = ModelManager()