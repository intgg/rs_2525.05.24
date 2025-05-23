"""
音频捕获模块测试
===============
测试音频捕获和语音识别功能
"""

import pytest
import asyncio
import time
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.audio_capture import AudioCaptureModule
from utils.audio_utils import AudioDeviceManager, AudioProcessor, AudioRecorder
from utils.logger import get_logger


class TestAudioCapture:
    """音频捕获功能测试"""

    def setup_method(self):
        """测试前设置"""
        self.logger = get_logger("test_audio")
        self.recognized_texts = []
        self.errors = []

        # 设置回调函数
        def text_callback(text, is_final):
            self.recognized_texts.append((text, is_final))
            print(f"识别结果 (final={is_final}): {text}")

        def error_callback(error):
            self.errors.append(error)
            print(f"错误: {error}")

        self.audio_module = AudioCaptureModule(
            text_callback=text_callback,
            error_callback=error_callback
        )

    @pytest.mark.asyncio
    async def test_model_initialization(self):
        """测试模型初始化"""
        print("\n=== 测试模型初始化 ===")

        success = await self.audio_module.initialize_models()
        assert success, "模型初始化失败"

        # 检查模型是否加载
        assert self.audio_module.asr_model is not None, "ASR模型未加载"

        print("✅ 模型初始化测试通过")

    def test_audio_device_detection(self):
        """测试音频设备检测"""
        print("\n=== 测试音频设备检测 ===")

        devices = AudioDeviceManager.list_audio_devices()
        assert len(devices) > 0, "未检测到音频设备"

        print(f"检测到 {len(devices)} 个音频设备:")
        for device in devices:
            if device['max_input_channels'] > 0:
                print(f"  - {device['name']} (输入通道: {device['max_input_channels']})")

        # 获取默认输入设备
        default_device = AudioDeviceManager.get_default_input_device()
        if default_device:
            print(f"默认输入设备: {default_device['name']}")

        print("✅ 音频设备检测测试通过")

    @pytest.mark.asyncio
    async def test_audio_capture_basic(self):
        """测试基本音频捕获功能"""
        print("\n=== 测试基本音频捕获 ===")

        # 初始化模型
        await self.audio_module.initialize_models()

        # 启动捕获
        success = self.audio_module.start_capture()
        assert success, "音频捕获启动失败"

        print("音频捕获已启动，等待5秒...")
        print("请对着麦克风说话进行测试...")

        # 运行5秒
        await asyncio.sleep(5)

        # 停止捕获
        self.audio_module.stop_capture()

        print(f"捕获结束，识别到 {len(self.recognized_texts)} 个文本片段")

        # 检查是否有识别结果
        final_texts = [text for text, is_final in self.recognized_texts if is_final]
        if final_texts:
            print("最终识别结果:")
            for text in final_texts:
                print(f"  - {text}")

        print("✅ 基本音频捕获测试完成")

    def test_audio_processing(self):
        """测试音频处理功能"""
        print("\n=== 测试音频处理功能 ===")

        # 生成测试音频数据
        sample_rate = 16000
        duration = 2.0
        frequency = 440  # A4音符

        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = 0.5 * np.sin(2 * np.pi * frequency * t)

        # 测试归一化
        normalized = AudioProcessor.normalize_audio(test_audio, target_rms=0.1)
        assert np.abs(np.sqrt(np.mean(normalized ** 2)) - 0.1) < 0.01, "音频归一化失败"

        # 测试分块
        chunk_size = 8000
        chunks = AudioProcessor.chunk_audio(test_audio, chunk_size)
        assert len(chunks) > 0, "音频分块失败"

        # 测试带通滤波
        filtered = AudioProcessor.apply_bandpass_filter(test_audio)
        assert len(filtered) == len(test_audio), "带通滤波失败"

        print("✅ 音频处理功能测试通过")

    @pytest.mark.asyncio
    async def test_vad_functionality(self):
        """测试VAD功能"""
        print("\n=== 测试VAD功能 ===")

        # 启用VAD
        self.audio_module.audio_config.use_vad = True

        # 初始化模型
        await self.audio_module.initialize_models()

        if self.audio_module.vad_model is None:
            print("⚠️  VAD模型未加载，跳过VAD测试")
            return

        print("VAD模型已加载，开始测试...")

        # 启动捕获
        success = self.audio_module.start_capture()
        assert success, "VAD音频捕获启动失败"

        print("请说话测试VAD检测（10秒）...")
        print("VAD会检测语音的开始和结束")

        await asyncio.sleep(10)

        self.audio_module.stop_capture()

        print("✅ VAD功能测试完成")

    def test_audio_recorder(self):
        """测试音频录制器"""
        print("\n=== 测试音频录制器 ===")

        recorder = AudioRecorder(sample_rate=16000)

        print("开始录制3秒...")
        success = recorder.start_recording()
        assert success, "录制启动失败"

        time.sleep(3)

        audio_data = recorder.stop_recording()
        assert len(audio_data) > 0, "未录制到音频数据"

        print(f"录制完成，音频长度: {len(audio_data)} 采样点")
        print(f"录制时长: {len(audio_data) / 16000:.2f} 秒")

        print("✅ 音频录制器测试通过")

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        print("\n=== 测试错误处理 ===")

        # 测试未初始化时启动捕获
        audio_module_uninit = AudioCaptureModule()
        success = audio_module_uninit.start_capture()
        assert not success, "未初始化的模块不应该能启动"

        print("✅ 错误处理测试通过")

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, 'audio_module') and self.audio_module.is_running():
            self.audio_module.stop_capture()


class TestAudioUtils:
    """音频工具测试"""

    def test_device_manager(self):
        """测试设备管理器"""
        print("\n=== 测试设备管理器 ===")

        devices = AudioDeviceManager.list_audio_devices()
        print(f"音频设备数量: {len(devices)}")

        default_device = AudioDeviceManager.get_default_input_device()
        if default_device:
            print(f"默认设备: {default_device['name']}")

            # 测试设备（如果有默认设备）
            if default_device['channels'] > 0:
                print("测试默认输入设备...")
                # 注意：实际测试时请确保有音频输入
                # test_result = AudioDeviceManager.test_audio_device(default_device['id'])
                # assert test_result, "设备测试失败"

        print("✅ 设备管理器测试通过")


def run_interactive_test():
    """运行交互式测试"""
    print("🎙️ 音频捕获交互式测试")
    print("=" * 50)

    async def interactive_test():
        # 创建测试实例
        test_instance = TestAudioCapture()
        test_instance.setup_method()

        try:
            # 测试设备
            print("\n1. 测试音频设备...")
            test_instance.test_audio_device_detection()

            # 测试模型初始化
            print("\n2. 初始化模型...")
            await test_instance.test_model_initialization()

            # 交互式语音测试
            print("\n3. 开始语音识别测试...")
            print("请准备对着麦克风说话...")
            input("按回车键开始...")

            await test_instance.test_audio_capture_basic()

        except KeyboardInterrupt:
            print("\n测试被中断")
        finally:
            test_instance.teardown_method()

    asyncio.run(interactive_test())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="音频捕获模块测试")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="运行交互式测试")
    parser.add_argument("--pytest", "-p", action="store_true",
                        help="运行pytest测试")

    args = parser.parse_args()

    if args.interactive:
        run_interactive_test()
    elif args.pytest:
        # 运行pytest
        pytest.main([__file__, "-v"])
    else:
        print("请选择测试模式:")
        print("  --interactive  交互式测试")
        print("  --pytest      自动化测试")

        choice = input("\n选择模式 (i/p): ").strip().lower()
        if choice in ['i', 'interactive']:
            run_interactive_test()
        else:
            pytest.main([__file__, "-v"])