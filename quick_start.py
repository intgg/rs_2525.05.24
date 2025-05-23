#!/usr/bin/env python3
"""
实时语音翻译系统 - 快速启动脚本
==============================
提供简化的启动选项和预设配置
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from modules.pipeline import RealTimeTranslationPipeline
from config.settings import config
from utils.logger import get_logger


class QuickStart:
    """快速启动管理器"""

    def __init__(self):
        self.pipeline = RealTimeTranslationPipeline()
        self.logger = get_logger("quick_start")

        # 预设配置
        self.presets = {
            "中英互译": {
                "source": "zh",
                "target": "en",
                "description": "中文语音识别 -> 英文翻译和语音"
            },
            "英中互译": {
                "source": "en",
                "target": "zh",
                "description": "英文语音识别 -> 中文翻译和语音"
            },
            "中日互译": {
                "source": "zh",
                "target": "ja",
                "description": "中文语音识别 -> 日文翻译和语音"
            },
            "中韩互译": {
                "source": "zh",
                "target": "ko",
                "description": "中文语音识别 -> 韩文翻译和语音"
            },
            "会议模式": {
                "source": "zh",
                "target": "en",
                "description": "优化的会议翻译设置",
                "settings": {
                    "max_segment_duration": 10.0,
                    "use_vad": True,
                    "chunk_size": 256
                }
            }
        }

    def display_banner(self):
        """显示启动横幅"""
        print("=" * 80)
        print("🎙️  实时语音翻译系统 - 快速启动")
        print("=" * 80)
        print("🚀 快速配置并启动语音翻译服务")
        print("💡 支持多语言实时翻译，一键开始使用")
        print("-" * 80)

    def show_presets(self):
        """显示预设配置"""
        print("\n📋 可用的预设配置:")
        print("-" * 50)

        for i, (name, preset) in enumerate(self.presets.items(), 1):
            print(f"{i}. {name}")
            print(f"   {preset['description']}")
            print()

    def get_user_choice(self) -> tuple:
        """获取用户选择"""
        self.show_presets()

        try:
            choice = input("请选择预设配置 (输入数字) 或按回车使用默认配置: ").strip()

            if not choice:
                # 默认配置
                return "zh", "en", {}

            choice_num = int(choice)
            preset_names = list(self.presets.keys())

            if 1 <= choice_num <= len(preset_names):
                preset_name = preset_names[choice_num - 1]
                preset = self.presets[preset_name]

                source_lang = preset["source"]
                target_lang = preset["target"]
                settings = preset.get("settings", {})

                print(f"\n✅ 已选择: {preset_name}")
                print(f"   翻译方向: {source_lang} -> {target_lang}")

                return source_lang, target_lang, settings
            else:
                print("❌ 无效选择，使用默认配置")
                return "zh", "en", {}

        except (ValueError, KeyboardInterrupt):
            print("\n使用默认配置...")
            return "zh", "en", {}

    def apply_settings(self, settings: dict):
        """应用自定义设置"""
        if not settings:
            return

        print("\n⚙️  应用自定义设置...")

        # 应用音频设置
        if "max_segment_duration" in settings:
            config.audio.max_segment_duration_seconds = settings["max_segment_duration"]
            print(f"   最大片段时长: {settings['max_segment_duration']}s")

        if "use_vad" in settings:
            config.audio.use_vad = settings["use_vad"]
            print(f"   VAD检测: {'启用' if settings['use_vad'] else '禁用'}")

        # 应用翻译设置
        if "chunk_size" in settings:
            config.translation.chunk_size = settings["chunk_size"]
            print(f"   翻译块大小: {settings['chunk_size']}")

    def setup_callbacks(self):
        """设置回调函数"""

        def on_text(text, is_final):
            if is_final:
                print(f"\n🎤 [识别完成] {text}")
            else:
                print(f"\r🎤 [识别中] {text}...", end="", flush=True)

        def on_translation(translation, is_final):
            if is_final:
                print(f"🌍 [翻译完成] {translation}")
                print(f"🔊 [播放中] 正在播放翻译结果...")
            else:
                print(f"\r🌍 [翻译中] {translation}...", end="", flush=True)

        def on_status(status, data):
            if "初始化" in status or "启动" in status or "停止" in status:
                print(f"\n📊 {status}")

        def on_error(error):
            print(f"\n❌ 错误: {error}")

        self.pipeline.add_text_callback(on_text)
        self.pipeline.add_translation_callback(on_translation)
        self.pipeline.add_status_callback(on_status)
        self.pipeline.add_error_callback(on_error)

    async def run_quick_start(self):
        """运行快速启动流程"""
        try:
            self.display_banner()

            # 获取用户选择
            source_lang, target_lang, settings = self.get_user_choice()

            # 应用设置
            self.apply_settings(settings)

            # 设置回调
            self.setup_callbacks()

            print(f"\n🚀 正在初始化翻译系统...")
            print(f"📡 翻译方向: {source_lang} -> {target_lang}")

            # 初始化系统
            success = await self.pipeline.initialize(source_lang, target_lang)
            if not success:
                print("❌ 系统初始化失败")
                return False

            print("\n✅ 系统初始化完成!")
            print("\n💡 使用说明:")
            print("   • 对着麦克风说话，系统会自动识别并翻译")
            print("   • 支持连续语音识别和翻译")
            print("   • 按 Ctrl+C 停止翻译")
            print("\n" + "=" * 60)

            # 启动翻译
            success = self.pipeline.start_translation()
            if not success:
                print("❌ 翻译服务启动失败")
                return False

            print("🟢 翻译服务已启动，请开始说话...")
            print("\n" + "-" * 60)

            # 保持运行
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️  用户请求停止翻译...")

            return True

        except Exception as e:
            print(f"\n❌ 启动过程出错: {e}")
            return False

        finally:
            # 清理资源
            print("\n🧹 正在清理资源...")
            if self.pipeline.is_running:
                self.pipeline.stop_translation()
            print("✅ 清理完成，程序退出")

    def run_demo_mode(self):
        """运行演示模式"""
        print("\n🎭 演示模式")
        print("-" * 30)
        print("这是一个快速演示，展示系统的主要功能")

        # 模拟翻译过程
        demo_texts = [
            ("你好，欢迎使用实时语音翻译系统", "Hello, welcome to the real-time speech translation system"),
            ("这个系统支持多种语言", "This system supports multiple languages"),
            ("翻译质量非常好", "The translation quality is very good")
        ]

        print("\n📺 演示翻译效果:")
        for source, target in demo_texts:
            print(f"\n🎤 [中文] {source}")
            print(f"🌍 [英文] {target}")

        print("\n💡 要体验实际功能，请选择非演示模式")

    def show_help(self):
        """显示帮助信息"""
        print("\n📖 快速启动帮助")
        print("=" * 40)
        print("\n🎯 主要功能:")
        print("  • 实时语音识别")
        print("  • 多语言机器翻译")
        print("  • 语音合成播放")
        print("\n⚙️  支持的语言:")
        print("  • 中文 (zh) - 支持语音识别")
        print("  • 英语 (en) - 支持翻译和TTS")
        print("  • 日语 (ja) - 支持翻译和TTS")
        print("  • 韩语 (ko) - 支持翻译和TTS")
        print("  • 法语 (fr) - 支持翻译和TTS")
        print("  • 德语 (de) - 支持翻译和TTS")
        print("\n🔧 系统要求:")
        print("  • Python 3.7+")
        print("  • 音频输入设备 (麦克风)")
        print("  • 网络连接")
        print("  • 2GB+ 内存")
        print("\n📞 获取帮助:")
        print("  • GitHub: https://github.com/your-repo/real-time-translator")
        print("  • 文档: README.md")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实时语音翻译系统 - 快速启动")
    parser.add_argument("--demo", action="store_true", help="演示模式")
    parser.add_argument("--help-quick", action="store_true", help="显示快速帮助")
    parser.add_argument("--source", default="zh", help="源语言 (默认: zh)")
    parser.add_argument("--target", default="en", help="目标语言 (默认: en)")
    parser.add_argument("--no-vad", action="store_true", help="禁用VAD")
    parser.add_argument("--no-punc", action="store_true", help="禁用标点恢复")

    args = parser.parse_args()

    quick_start = QuickStart()

    if args.help_quick:
        quick_start.show_help()
        return

    if args.demo:
        quick_start.run_demo_mode()
        return

    # 应用命令行参数
    if args.no_vad:
        config.audio.use_vad = False
    if args.no_punc:
        config.audio.use_punctuation = False

    # 如果指定了语言参数，直接使用
    if args.source != "zh" or args.target != "en":
        config.update_language_pair(args.source, args.target)

        print(f"🌐 使用命令行指定的语言对: {args.source} -> {args.target}")

        quick_start.setup_callbacks()

        success = await quick_start.pipeline.initialize(args.source, args.target)
        if success:
            success = quick_start.pipeline.start_translation()
            if success:
                try:
                    print("🟢 翻译服务已启动，请开始说话...")
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n⏹️  停止翻译...")
                finally:
                    quick_start.pipeline.stop_translation()
    else:
        # 运行交互式快速启动
        await quick_start.run_quick_start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        sys.exit(1)