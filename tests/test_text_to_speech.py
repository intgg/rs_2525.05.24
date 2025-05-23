"""
语音合成模块测试
===============
测试TTS功能和音频播放
"""

import pytest
import asyncio
import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.text_to_speech import TextToSpeechModule
from config.settings import config
from utils.logger import get_logger


class TestTextToSpeechModule:
    """语音合成模块测试"""

    def setup_method(self):
        """测试前设置"""
        self.logger = get_logger("test_tts")
        self.playback_events = []
        self.errors = []

        # 设置回调函数
        def playback_callback(text, is_playing):
            self.playback_events.append((text, is_playing))
            status = "开始播放" if is_playing else "播放完成"
            print(f"播放状态: {status} - {text[:30]}...")

        def error_callback(error):
            self.errors.append(error)
            print(f"错误: {error}")

        self.tts_module = TextToSpeechModule(
            playback_callback=playback_callback,
            error_callback=error_callback
        )

    @pytest.mark.asyncio
    async def test_voice_loading(self):
        """测试音色加载"""
        print("\n=== 测试音色加载 ===")

        # 加载可用音色
        await self.tts_module.load_available_voices()

        assert self.tts_module.voices_loaded, "音色未加载"
        assert len(self.tts_module.available_voices) > 0, "未找到可用音色"

        print(f"加载了 {len(self.tts_module.available_voices)} 种语言的音色")

        # 测试获取特定语言的音色
        en_voices = self.tts_module.get_voices_for_language("en-US")
        zh_voices = self.tts_module.get_voices_for_language("zh-CN")

        print(f"英语音色数量: {len(en_voices)}")
        print(f"中文音色数量: {len(zh_voices)}")

        print("✅ 音色加载测试通过")

    @pytest.mark.asyncio
    async def test_speech_synthesis(self):
        """测试语音合成"""
        print("\n=== 测试语音合成 ===")

        # 加载音色
        await self.tts_module.load_available_voices()

        # 测试文本
        test_texts = [
            ("Hello, this is a test.", "en-US-AriaNeural"),
            ("你好，这是一个测试。", "zh-CN-XiaoxiaoNeural"),
            ("This is another test.", None)  # 使用默认音色
        ]

        for text, voice in test_texts:
            print(f"合成语音: {text}")

            # 测试语音合成
            audio_data = await self.tts_module._synthesize_speech(text, voice)

            assert audio_data is not None, f"语音合成失败: {text}"
            assert len(audio_data) > 0, f"音频数据为空: {text}"

            print(f"音频大小: {len(audio_data)} 字节")

        print("✅ 语音合成测试通过")

    @pytest.mark.asyncio
    async def test_immediate_speech(self):
        """测试立即语音播放"""
        print("\n=== 测试立即语音播放 ===")

        # 加载音色
        await self.tts_module.load_available_voices()

        # 测试立即播放
        test_text = "Hello, this is an immediate speech test."
        print(f"播放: {test_text}")

        success = self.tts_module.speak_immediate(test_text)
        assert success, "立即语音播放失败"

        # 检查播放事件
        assert len(self.playback_events) >= 2, "播放事件不完整"

        # 检查播放开始和结束事件
        start_events = [event for event in self.playback_events if event[1] == True]
        end_events = [event for event in self.playback_events if event[1] == False]

        assert len(start_events) > 0, "未检测到播放开始事件"
        assert len(end_events) > 0, "未检测到播放结束事件"

        print("✅ 立即语音播放测试通过")

    def test_tts_service(self):
        """测试TTS服务"""
        print("\n=== 测试TTS服务 ===")

        # 启动TTS服务
        success = self.tts_module.start_tts_service()
        assert success, "TTS服务启动失败"

        assert self.tts_module.running, "TTS服务未运行"

        # 添加语音任务
        test_texts = [
            "This is the first test.",
            "This is the second test.",
            "This is the final test."
        ]

        for i, text in enumerate(test_texts):
            priority = "high" if i == 1 else "normal"
            print(f"添加语音任务: {text} (优先级: {priority})")
            self.tts_module.speak(text, priority=priority)

        # 等待播放完成
        time.sleep(10)

        # 停止TTS服务
        self.tts_module.stop_tts_service()

        assert not self.tts_module.running, "TTS服务未停止"

        print("✅ TTS服务测试通过")

    @pytest.mark.asyncio
    async def test_voice_selection(self):
        """测试音色选择"""
        print("\n=== 测试音色选择 ===")

        # 加载音色
        await self.tts_module.load_available_voices()

        # 测试设置特定音色
        original_voice = self.tts_module.current_voice
        new_voice = "en-US-JennyNeural"

        self.tts_module.set_voice(new_voice)
        assert self.tts_module.current_voice == new_voice, "音色设置失败"

        # 测试为语言设置最佳音色
        best_zh_voice = self.tts_module.set_voice_for_language("zh-CN")
        assert "zh-CN" in best_zh_voice, "中文音色设置失败"

        best_en_voice = self.tts_module.set_voice_for_language("en-US")
        assert "en-US" in best_en_voice, "英文音色设置失败"

        print(f"中文最佳音色: {best_zh_voice}")
        print(f"英文最佳音色: {best_en_voice}")

        print("✅ 音色选择测试通过")

    def test_voice_listing(self):
        """测试音色列表功能"""
        print("\n=== 测试音色列表 ===")

        # 加载音色
        asyncio.run(self.tts_module.load_available_voices())

        # 获取所有音色
        all_voices = self.tts_module.list_available_voices()
        assert len(all_voices) > 0, "未获取到音色列表"

        # 获取特定语言的音色
        en_voices = self.tts_module.list_available_voices("en-US")
        assert "en-US" in en_voices, "未获取到英文音色"

        zh_voices = self.tts_module.list_available_voices("zh-CN")
        assert "zh-CN" in zh_voices, "未获取到中文音色"

        print(f"总语言数: {len(all_voices)}")
        print(f"英文音色数: {len(en_voices.get('en-US', []))}")
        print(f"中文音色数: {len(zh_voices.get('zh-CN', []))}")

        print("✅ 音色列表测试通过")

    def test_playback_control(self):
        """测试播放控制"""
        print("\n=== 测试播放控制 ===")

        # 启动TTS服务
        self.tts_module.start_tts_service()

        # 开始播放长文本
        long_text = "This is a very long text that will take some time to play. " * 5
        self.tts_module.speak(long_text)

        # 等待播放开始
        time.sleep(2)

        # 测试停止当前播放
        if self.tts_module.is_playing:
            print("停止当前播放...")
            self.tts_module.stop_current_playback()
            assert not self.tts_module.is_playing, "播放未停止"

        # 停止服务
        self.tts_module.stop_tts_service()

        print("✅ 播放控制测试通过")

    def test_tts_stats(self):
        """测试TTS统计功能"""
        print("\n=== 测试TTS统计 ===")

        # 执行一些TTS操作
        asyncio.run(self.tts_module.load_available_voices())
        self.tts_module.speak_immediate("Test statistics.")

        # 获取统计信息
        stats = self.tts_module.get_tts_stats()

        assert "total_synthesis" in stats, "统计信息缺少合成次数"
        assert "average_synthesis_time" in stats, "统计信息缺少平均合成时间"
        assert "current_voice" in stats, "统计信息缺少当前音色"
        assert "available_languages" in stats, "统计信息缺少可用语言数"

        print(f"TTS统计: {stats}")

        print("✅ TTS统计测试通过")

    def test_error_handling(self):
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")

        # 测试未启动服务时的操作
        tts_uninit = TextToSpeechModule()
        tts_uninit.speak("This should fail")

        # 测试空文本
        success = self.tts_module.speak_immediate("")
        assert not success, "空文本应该返回失败"

        success = self.tts_module.speak_immediate(None)
        assert not success, "None文本应该返回失败"

        print("✅ 错误处理测试通过")

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, 'tts_module') and self.tts_module.running:
            self.tts_module.stop_tts_service()


class TestTTSIntegration:
    """TTS集成测试"""

    @pytest.mark.asyncio
    async def test_multilingual_tts(self):
        """测试多语言TTS"""
        print("\n=== 测试多语言TTS ===")

        tts_module = TextToSpeechModule()
        await tts_module.load_available_voices()

        # 测试多种语言
        multilingual_tests = [
            ("Hello, how are you?", "en-US"),
            ("你好，你好吗？", "zh-CN"),
            ("こんにちは、元気ですか？", "ja-JP"),
            ("Bonjour, comment allez-vous?", "fr-FR")
        ]

        for text, lang in multilingual_tests:
            print(f"测试 {lang}: {text}")

            # 设置语言对应的音色
            voice = tts_module.set_voice_for_language(lang)
            print(f"使用音色: {voice}")

            # 合成语音
            success = tts_module.speak_immediate(text)
            if success:
                print(f"✅ {lang} 语音合成成功")
            else:
                print(f"❌ {lang} 语音合成失败")

        print("✅ 多语言TTS测试完成")


def run_interactive_test():
    """运行交互式测试"""
    print("🔊 TTS模块交互式测试")
    print("=" * 50)

    async def interactive_test():
        test_instance = TestTextToSpeechModule()
        test_instance.setup_method()

        try:
            # 测试音色加载
            print("\n1. 加载可用音色...")
            await test_instance.test_voice_loading()

            # 交互式TTS测试
            print("\n2. 交互式TTS测试...")
            print("注意：请确保音响或耳机已连接")

            while True:
                text = input("\n请输入要播放的文本 (输入'quit'退出): ").strip()
                if text.lower() == 'quit':
                    break

                if text:
                    # 选择语言
                    lang_choice = input("选择语言 (en/zh/auto): ").strip().lower()

                    if lang_choice == "zh":
                        test_instance.tts_module.set_voice_for_language("zh-CN")
                    elif lang_choice == "en":
                        test_instance.tts_module.set_voice_for_language("en-US")
                    # auto 使用默认

                    print(f"正在播放: {text}")
                    success = test_instance.tts_module.speak_immediate(text)

                    if success:
                        print("✅ 播放完成")
                    else:
                        print("❌ 播放失败")

        except KeyboardInterrupt:
            print("\n测试被中断")
        finally:
            test_instance.teardown_method()

    asyncio.run(interactive_test())


def run_voice_demo():
    """运行音色演示"""
    print("🎵 TTS音色演示")
    print("=" * 30)

    async def voice_demo():
        tts_module = TextToSpeechModule()
        await tts_module.load_available_voices()

        # 演示不同音色
        demo_text = "Hello, this is a voice demonstration."
        voices_to_demo = [
            "en-US-AriaNeural",
            "en-US-JennyNeural",
            "en-GB-SoniaNeural",
            "zh-CN-XiaoxiaoNeural"
        ]

        for voice in voices_to_demo:
            print(f"\n播放音色: {voice}")
            print(f"文本: {demo_text}")

            tts_module.set_voice(voice)
            success = tts_module.speak_immediate(demo_text)

            if success:
                input("按回车继续下一个音色...")
            else:
                print("播放失败，跳过...")

        print("\n音色演示完成！")

    asyncio.run(voice_demo())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TTS模块测试")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="运行交互式测试")
    parser.add_argument("--demo", "-d", action="store_true",
                        help="运行音色演示")
    parser.add_argument("--pytest", "-p", action="store_true",
                        help="运行pytest测试")

    args = parser.parse_args()

    if args.interactive:
        run_interactive_test()
    elif args.demo:
        run_voice_demo()
    elif args.pytest:
        pytest.main([__file__, "-v"])
    else:
        print("请选择测试模式:")
        print("  --interactive  交互式测试")
        print("  --demo        音色演示")
        print("  --pytest      自动化测试")

        choice = input("\n选择模式 (i/d/p): ").strip().lower()
        if choice in ['i', 'interactive']:
            run_interactive_test()
        elif choice in ['d', 'demo']:
            run_voice_demo()
        else:
            pytest.main([__file__, "-v"])