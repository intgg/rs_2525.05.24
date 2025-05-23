"""
实时语音翻译系统 - 主程序
========================
基于FunASR + Transformers + Edge-TTS的实时语音翻译系统

使用方法:
    python main.py

功能特点:
- 实时语音识别（FunASR）
- 实时机器翻译（Hugging Face Transformers）
- 实时语音合成（Edge TTS）
- 模块化设计，易于扩展和维护
"""

import asyncio
import signal
import sys
import os
import time
from typing import Dict, List

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import config
from modules.pipeline import RealTimeTranslationPipeline


class TranslationSystemUI:
    """翻译系统用户界面"""

    def __init__(self):
        self.pipeline = RealTimeTranslationPipeline()
        self.setup_callbacks()
        self.running = True

        # 界面状态
        self.last_source_text = ""
        self.last_translation = ""

    def setup_callbacks(self):
        """设置回调函数"""
        self.pipeline.add_status_callback(self.on_status_change)
        self.pipeline.add_text_callback(self.on_text_recognized)
        self.pipeline.add_translation_callback(self.on_translation_result)
        self.pipeline.add_error_callback(self.on_error)

    def on_status_change(self, status: str, data: Dict):
        """处理状态变化"""
        print(f"\n[系统状态] {status}")
        if data:
            for key, value in data.items():
                print(f"  {key}: {value}")

    def on_text_recognized(self, text: str, is_final: bool):
        """处理语音识别结果"""
        if is_final:
            print(f"\n[识别完成] {text}")
            self.last_source_text = text
        else:
            # 实时显示识别中的文本
            print(f"\r[识别中] {text}...", end="", flush=True)

    def on_translation_result(self, translation: str, is_final: bool):
        """处理翻译结果"""
        if is_final:
            print(f"\n[翻译完成] {translation}")
            print(f"[播放中] 正在播放翻译结果...")
            self.last_translation = translation
        else:
            # 实时显示翻译中的文本
            print(f"\r[翻译中] {translation}...", end="", flush=True)

    def on_error(self, error_msg: str):
        """处理错误"""
        print(f"\n[错误] {error_msg}")

    def display_banner(self):
        """显示系统横幅"""
        print("=" * 80)
        print("🎙️  实时语音翻译系统  🌍")
        print("=" * 80)
        print("基于 FunASR + Transformers + Edge-TTS")
        print("支持多语言实时语音识别、翻译和语音合成")
        print("-" * 80)

    def display_language_menu(self):
        """显示语言选择菜单"""
        print("\n📋 支持的语言:")
        languages = {
            "zh": "中文 (Chinese)",
            "en": "英语 (English)",
            "ja": "日语 (Japanese)",
            "ko": "韩语 (Korean)",
            "fr": "法语 (French)",
            "de": "德语 (German)",
            "es": "西班牙语 (Spanish)",
            "ru": "俄语 (Russian)"
        }

        for i, (code, name) in enumerate(languages.items(), 1):
            print(f"{i}. {code} - {name}")

        return languages

    def get_language_choice(self, prompt: str, languages: Dict[str, str]) -> str:
        """获取用户语言选择"""
        while True:
            try:
                choice = input(f"\n{prompt} (输入数字): ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    lang_codes = list(languages.keys())
                    if 0 <= index < len(lang_codes):
                        return lang_codes[index]

                print("❌ 无效选择，请重新输入")
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
                sys.exit(0)

    def display_main_menu(self):
        """显示主菜单"""
        print("\n🎯 主菜单:")
        print("1. 开始翻译")
        print("2. 更改语言对")
        print("3. 查看系统状态")
        print("4. 查看可用音色")
        print("5. 测试翻译")
        print("6. 清空上下文")
        print("0. 退出系统")

    def get_menu_choice(self) -> str:
        """获取菜单选择"""
        return input("\n请选择操作 (输入数字): ").strip()

    async def initialize_system(self):
        """初始化系统"""
        print("\n🚀 正在初始化系统...")

        # 显示语言选择
        languages = self.display_language_menu()

        print("\n请选择翻译语言对:")
        source_lang = self.get_language_choice("选择源语言 (说话语言)", languages)
        target_lang = self.get_language_choice("选择目标语言 (翻译目标)", languages)

        if source_lang == target_lang:
            print("⚠️  源语言和目标语言相同，将使用默认语言对 zh->en")
            source_lang, target_lang = "zh", "en"

        print(f"\n🌐 翻译方向: {languages[source_lang]} -> {languages[target_lang]}")

        # 初始化管道
        success = await self.pipeline.initialize(source_lang, target_lang)
        if success:
            print("\n✅ 系统初始化成功!")
            return True
        else:
            print("\n❌ 系统初始化失败!")
            return False

    async def start_translation_session(self):
        """开始翻译会话"""
        if not self.pipeline.is_initialized:
            print("❌ 系统未初始化，请先初始化系统")
            return

        print("\n🎙️  启动实时翻译...")
        print("💡 使用说明:")
        print("   - 对着麦克风说话，系统会自动识别并翻译")
        print("   - 按 Ctrl+C 停止翻译")
        print("   - 支持VAD自动检测语音开始/结束")
        print("-" * 50)

        success = self.pipeline.start_translation()
        if success:
            print("🟢 翻译服务已启动，请开始说话...")

            try:
                # 保持翻译会话运行
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️  停止翻译会话...")
                self.pipeline.stop_translation()
                print("✅ 翻译会话已停止")
        else:
            print("❌ 翻译服务启动失败")

    async def change_language_pair(self):
        """更改翻译语言对"""
        print("\n🔄 更改翻译语言对")
        languages = self.display_language_menu()

        source_lang = self.get_language_choice("选择新的源语言", languages)
        target_lang = self.get_language_choice("选择新的目标语言", languages)

        if source_lang == target_lang:
            print("⚠️  源语言和目标语言不能相同")
            return

        print(f"\n🔄 正在切换到: {languages[source_lang]} -> {languages[target_lang]}")
        success = self.pipeline.change_language_pair(source_lang, target_lang)

        if success:
            print("✅ 语言对更改成功!")
        else:
            print("❌ 语言对更改失败!")

    def show_system_status(self):
        """显示系统状态"""
        print("\n📊 系统状态:")
        print("-" * 50)

        status = self.pipeline.get_pipeline_status()

        # 基本状态
        print(f"初始化状态: {'✅ 已初始化' if status['is_initialized'] else '❌ 未初始化'}")
        print(f"运行状态: {'🟢 运行中' if status['is_running'] else '🔴 已停止'}")

        # 当前会话
        if status['current_session']:
            session = status['current_session']
            print(f"\n当前会话:")
            print(f"  会话ID: {session['session_id']}")
            print(f"  语言对: {session['source_language']} -> {session['target_language']}")
            print(f"  运行时长: {session['runtime']:.1f} 秒")
            print(f"  识别文本长度: {session['total_text_length']} 字符")
            print(f"  翻译次数: {session['total_translations']}")

        # 性能统计
        perf = status['performance_stats']
        print(f"\n性能统计:")
        print(f"  总会话数: {perf['sessions_count']}")
        print(f"  总运行时间: {perf['total_runtime']:.1f} 秒")
        print(f"  错误次数: {perf['error_count']}")

        # 模块状态
        if 'module_status' in status:
            print(f"\n模块状态:")
            for module, stats in status['module_status'].items():
                print(f"  {module}: {stats}")

    def show_available_voices(self):
        """显示可用音色"""
        print("\n🎵 可用音色:")
        print("-" * 50)

        voices = self.pipeline.get_available_voices()
        for lang, voice_list in voices.items():
            print(f"\n{lang}:")
            for voice in voice_list[:3]:  # 只显示前3个音色
                print(f"  • {voice['name']} ({voice['gender']})")
            if len(voice_list) > 3:
                print(f"  ... 还有 {len(voice_list) - 3} 个音色")

    async def test_translation(self):
        """测试翻译功能"""
        if not self.pipeline.is_initialized:
            print("❌ 系统未初始化")
            return

        test_text = input("\n输入要测试翻译的文本: ").strip()
        if not test_text:
            return

        print(f"\n🔄 正在翻译: {test_text}")

        # 模拟文本输入进行翻译测试
        if self.pipeline.translation_module:
            result = self.pipeline.translation_module.translate_immediate(test_text)
            if result:
                print(f"✅ 翻译结果: {result}")

                # 测试TTS
                play_choice = input("\n是否播放翻译结果? (y/n): ").strip().lower()
                if play_choice in ['y', 'yes', '是']:
                    if self.pipeline.tts_module:
                        success = self.pipeline.tts_module.speak_immediate(result)
                        if success:
                            print("🔊 播放完成")
                        else:
                            print("❌ 播放失败")
            else:
                print("❌ 翻译失败")

    def clear_context(self):
        """清空翻译上下文"""
        self.pipeline.clear_context()
        self.last_source_text = ""
        self.last_translation = ""
        print("\n🗑️  翻译上下文已清空")

    async def run(self):
        """运行主程序"""
        self.display_banner()

        # 系统初始化
        if not await self.initialize_system():
            print("❌ 系统初始化失败，程序退出")
            return

        # 主循环
        while self.running:
            try:
                self.display_main_menu()
                choice = self.get_menu_choice()

                if choice == "1":
                    await self.start_translation_session()
                elif choice == "2":
                    await self.change_language_pair()
                elif choice == "3":
                    self.show_system_status()
                elif choice == "4":
                    self.show_available_voices()
                elif choice == "5":
                    await self.test_translation()
                elif choice == "6":
                    self.clear_context()
                elif choice == "0":
                    break
                else:
                    print("❌ 无效选择，请重新输入")

            except KeyboardInterrupt:
                print("\n\n👋 用户请求退出...")
                break
            except Exception as e:
                print(f"\n❌ 程序错误: {e}")

        # 清理资源
        print("\n🧹 正在清理资源...")
        if self.pipeline.is_running:
            self.pipeline.stop_translation()
        print("✅ 程序已安全退出")


def setup_signal_handlers(ui_instance):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        print("\n\n⚠️  收到退出信号，正在安全关闭...")
        ui_instance.running = False
        if ui_instance.pipeline.is_running:
            ui_instance.pipeline.emergency_stop()
        print("✅ 程序已安全退出")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    print("🚀 启动实时语音翻译系统...")

    try:
        # 创建UI实例
        ui = TranslationSystemUI()

        # 设置信号处理
        setup_signal_handlers(ui)

        # 运行主程序
        await ui.run()

    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)

    # 运行主程序
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        sys.exit(1)