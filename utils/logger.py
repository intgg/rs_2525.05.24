"""
日志系统模块
===========
提供统一的日志记录功能，支持文件和控制台输出
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import json
import threading
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',  # 青色
        'INFO': '\033[32m',  # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',  # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'  # 重置
    }

    def format(self, record):
        # 添加颜色
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


class TranslationLogger:
    """翻译系统专用日志器"""

    def __init__(self, name: str = "translation_system",
                 log_dir: str = "./logs",
                 log_level: str = "INFO",
                 enable_console: bool = True,
                 enable_file: bool = True,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):

        self.name = name
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper())
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)

        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()

        # 性能日志
        self.performance_logger = self._setup_performance_logger()

        # 错误统计
        self.error_stats = {
            'audio_errors': 0,
            'translation_errors': 0,
            'tts_errors': 0,
            'system_errors': 0,
            'last_error_time': None
        }

        # 线程锁
        self._lock = threading.Lock()

    def _setup_handlers(self):
        """设置日志处理器"""
        # 控制台处理器
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)

            # 使用彩色格式化器
            console_formatter = ColorFormatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # 文件处理器
        if self.enable_file:
            # 主日志文件（按大小轮转）
            main_log_file = self.log_dir / f"{self.name}.log"
            file_handler = RotatingFileHandler(
                main_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)

            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # 错误日志文件（只记录ERROR和CRITICAL）
            error_log_file = self.log_dir / f"{self.name}_errors.log"
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            self.logger.addHandler(error_handler)

    def _setup_performance_logger(self):
        """设置性能日志器"""
        perf_logger = logging.getLogger(f"{self.name}_performance")
        perf_logger.setLevel(logging.INFO)

        if not perf_logger.handlers:
            perf_log_file = self.log_dir / f"{self.name}_performance.log"
            perf_handler = TimedRotatingFileHandler(
                perf_log_file,
                when='midnight',
                interval=1,
                backupCount=7,
                encoding='utf-8'
            )

            perf_formatter = logging.Formatter(
                '%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            perf_handler.setFormatter(perf_formatter)
            perf_logger.addHandler(perf_handler)

        return perf_logger

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self.logger.debug(self._format_message(message, **kwargs))

    def info(self, message: str, **kwargs):
        """记录信息"""
        self.logger.info(self._format_message(message, **kwargs))

    def warning(self, message: str, **kwargs):
        """记录警告"""
        self.logger.warning(self._format_message(message, **kwargs))

    def error(self, message: str, error_type: str = "system", **kwargs):
        """记录错误"""
        with self._lock:
            # 更新错误统计
            error_key = f"{error_type}_errors"
            if error_key in self.error_stats:
                self.error_stats[error_key] += 1
            else:
                self.error_stats['system_errors'] += 1

            self.error_stats['last_error_time'] = datetime.now().isoformat()

        self.logger.error(self._format_message(message, error_type=error_type, **kwargs))

    def critical(self, message: str, **kwargs):
        """记录严重错误"""
        self.logger.critical(self._format_message(message, **kwargs))

    def _format_message(self, message: str, **kwargs) -> str:
        """格式化日志消息"""
        if kwargs:
            # 将kwargs转换为易读的字符串
            extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} | {extra_info}"
        return message

    def log_audio_event(self, event_type: str, details: Dict[str, Any]):
        """记录音频事件"""
        self.info(f"Audio Event: {event_type}", **details)

    def log_translation_event(self, source_text: str, translated_text: str,
                              source_lang: str, target_lang: str,
                              duration: float):
        """记录翻译事件"""
        self.info(
            f"Translation: {source_lang}->{target_lang}",
            source_length=len(source_text),
            target_length=len(translated_text),
            duration=f"{duration:.3f}s",
            source_preview=source_text[:50] + "..." if len(source_text) > 50 else source_text
        )

    def log_tts_event(self, text: str, voice: str, duration: float):
        """记录TTS事件"""
        self.info(
            f"TTS: {voice}",
            text_length=len(text),
            duration=f"{duration:.3f}s",
            text_preview=text[:50] + "..." if len(text) > 50 else text
        )

    def log_performance(self, metric_name: str, value: float, unit: str = "",
                        context: Dict[str, Any] = None):
        """记录性能指标"""
        perf_data = {
            'metric': metric_name,
            'value': value,
            'unit': unit,
            'timestamp': time.time()
        }

        if context:
            perf_data.update(context)

        self.performance_logger.info(json.dumps(perf_data, ensure_ascii=False))

    def log_session_start(self, session_id: str, source_lang: str, target_lang: str):
        """记录会话开始"""
        self.info(
            f"Session Started: {session_id}",
            source_language=source_lang,
            target_language=target_lang,
            timestamp=datetime.now().isoformat()
        )

    def log_session_end(self, session_id: str, duration: float, stats: Dict[str, Any]):
        """记录会话结束"""
        self.info(
            f"Session Ended: {session_id}",
            duration=f"{duration:.1f}s",
            **stats
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            return self.error_stats.copy()

    def reset_error_stats(self):
        """重置错误统计"""
        with self._lock:
            for key in self.error_stats:
                if key.endswith('_errors'):
                    self.error_stats[key] = 0
            self.error_stats['last_error_time'] = None

    def set_level(self, level: str):
        """设置日志级别"""
        log_level = getattr(logging, level.upper())
        self.logger.setLevel(log_level)
        for handler in self.logger.handlers:
            handler.setLevel(log_level)


class LogManager:
    """日志管理器 - 管理多个日志器"""

    def __init__(self):
        self.loggers: Dict[str, TranslationLogger] = {}
        self.default_config = {
            'log_level': 'INFO',
            'enable_console': True,
            'enable_file': True,
            'log_dir': './logs'
        }

    def get_logger(self, name: str, **config) -> TranslationLogger:
        """获取或创建日志器"""
        if name not in self.loggers:
            logger_config = {**self.default_config, **config}
            self.loggers[name] = TranslationLogger(name, **logger_config)

        return self.loggers[name]

    def set_global_level(self, level: str):
        """设置所有日志器的级别"""
        for logger in self.loggers.values():
            logger.set_level(level)

    def get_all_error_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有日志器的错误统计"""
        all_stats = {}
        for name, logger in self.loggers.items():
            all_stats[name] = logger.get_error_stats()
        return all_stats

    def reset_all_error_stats(self):
        """重置所有日志器的错误统计"""
        for logger in self.loggers.values():
            logger.reset_error_stats()


# 全局日志管理器实例
log_manager = LogManager()


# 便捷函数
def get_logger(name: str = "translation_system", **config) -> TranslationLogger:
    """获取日志器的便捷函数"""
    return log_manager.get_logger(name, **config)


# 装饰器
def log_execution_time(logger: Optional[TranslationLogger] = None,
                       metric_name: str = "execution_time"):
    """记录函数执行时间的装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log_performance(
                    f"{func.__name__}_{metric_name}",
                    execution_time,
                    "seconds"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed after {execution_time:.3f}s: {e}",
                    function=func.__name__
                )
                raise

        return wrapper

    return decorator


def log_errors(logger: Optional[TranslationLogger] = None,
               error_type: str = "system"):
    """自动记录异常的装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    error_type=error_type,
                    function=func.__name__
                )
                raise

        return wrapper

    return decorator