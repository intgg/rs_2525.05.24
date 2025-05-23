"""
翻译模块测试
===========
测试实时翻译功能和SimulTrans策略
"""

import pytest
import asyncio
import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.translator import TranslationModule, SimulTransStrategy
from config.settings import config
from utils.logger import get_logger


class TestTranslationModule:
    """翻译模块测试"""

    def setup_method(self):
        """测试前设置"""
        self.logger = get_logger("test_translator")
        self.translated_texts = []
        self.errors = []

        # 设置回调函数
        def translation_callback(text, is_final):
            self.translated_texts.append((text, is_final))
            print(f"翻译结果 (final={is_final}): {text}")

        def error_callback(error):
            self.errors.append(error)
            print(f"错误: {error}")

        self.translator = TranslationModule(
            translation_callback=translation_callback,
            error_callback=error_callback
        )

    @pytest.mark.asyncio
    async def test_model_initialization(self):
        """测试翻译模型初始化"""
        print("\n=== 测试翻译模型初始化 ===")

        # 测试中英翻译
        success = await self.translator.initialize_model("zh", "en")
        assert success, "中英翻译模型初始化失败"

        assert self.translator.model is not None, "翻译模型未加载"
        assert self.translator.tokenizer is not None, "分词器未加载"

        print("✅ 翻译模型初始化测试通过")

    @pytest.mark.asyncio
    async def test_immediate_translation(self):
        """测试立即翻译功能"""
        print("\n=== 测试立即翻译 ===")

        # 初始化模型
        await self.translator.initialize_model("zh", "en")

        # 测试文本
        test_texts = [
            "你好，世界！",
            "这是一个测试。",
            "实时语音翻译系统。",
            "今天天气很好。"
        ]

        for text in test_texts:
            print(f"翻译: {text}")
            translated = self.translator.translate_immediate(text)

            assert translated is not None, f"翻译失败: {text}"
            assert len(translated.strip()) > 0, f"翻译结果为空: {text}"

            print(f"结果: {translated}")

        print("✅ 立即翻译测试通过")

    @pytest.mark.asyncio
    async def test_translation_service(self):
        """测试翻译服务"""
        print("\n=== 测试翻译服务 ===")

        # 初始化模型
        await self.translator.initialize_model("zh", "en")

        # 启动翻译服务
        success = self.translator.start_translation_service()
        assert success, "翻译服务启动失败"

        # 添加翻译任务
        test_texts = [
            ("你好", False),
            ("你好，世界", False),
            ("你好，世界！", True),
            ("这是一个测试", True)
        ]

        for text, is_final in test_texts:
            print(f"添加翻译任务: {text} (final={is_final})")
            self.translator.add_translation_task(text, is_final)

        # 等待翻译完成
        await asyncio.sleep(5)

        # 停止翻译服务
        self.translator.stop_translation_service()

        # 检查结果
        assert len(self.translated_texts) > 0, "未收到翻译结果"

        final_translations = [text for text, is_final in self.translated_texts if is_final]
        assert len(final_translations) > 0, "未收到最终翻译结果"

        print(f"收到 {len(self.translated_texts)} 个翻译结果")
        print(f"最终翻译: {final_translations}")

        print("✅ 翻译服务测试通过")

    @pytest.mark.asyncio
    async def test_language_pair_change(self):
        """测试语言对切换"""
        print("\n=== 测试语言对切换 ===")

        # 初始化中英翻译
        await self.translator.initialize_model("zh", "en")
        original_model = self.translator.current_model_name

        # 测试中文翻译
        text = "你好，世界！"
        result1 = self.translator.translate_immediate(text)
        assert result1 is not None, "中英翻译失败"
        print(f"中英翻译: {text} -> {result1}")

        # 切换到英中翻译
        success = self.translator.change_language_pair("en", "zh")
        assert success, "语言对切换失败"

        # 等待模型切换完成
        await asyncio.sleep(2)

        # 测试英文翻译
        english_text = "Hello, world!"
        result2 = self.translator.translate_immediate(english_text)
        assert result2 is not None, "英中翻译失败"
        print(f"英中翻译: {english_text} -> {result2}")

        print("✅ 语言对切换测试通过")

    def test_translation_cache(self):
        """测试翻译缓存功能"""
        print("\n=== 测试翻译缓存 ===")

        # 初始化翻译器
        asyncio.run(self.translator.initialize_model("zh", "en"))

        # 翻译相同文本多次
        text = "你好，世界！"

        # 第一次翻译
        start_time = time.time()
        result1 = self.translator.translate_immediate(text)
        time1 = time.time() - start_time

        # 第二次翻译（应该使用缓存）
        start_time = time.time()
        result2 = self.translator.translate_immediate(text)
        time2 = time.time() - start_time

        assert result1 == result2, "缓存翻译结果不一致"
        assert time2 < time1, "缓存未生效，第二次翻译时间应该更短"

        print(f"第一次翻译时间: {time1:.3f}s")
        print(f"第二次翻译时间: {time2:.3f}s")
        print(f"缓存加速比: {time1 / time2:.2f}x")

        print("✅ 翻译缓存测试通过")

    def test_translation_stats(self):
        """测试翻译统计功能"""
        print("\n=== 测试翻译统计 ===")

        # 初始化翻译器
        asyncio.run(self.translator.initialize_model("zh", "en"))

        # 执行一些翻译
        test_texts = ["你好", "世界", "测试"]
        for text in test_texts:
            self.translator.translate_immediate(text)

        # 获取统计信息
        stats = self.translator.get_translation_stats()

        assert stats["total_translations"] >= len(test_texts), "翻译计数不正确"
        assert stats["average_time"] > 0, "平均翻译时间应该大于0"
        assert stats["cache_size"] >= len(test_texts), "缓存大小不正确"

        print(f"翻译统计: {stats}")

        print("✅ 翻译统计测试通过")

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, 'translator') and self.translator.running:
            self.translator.stop_translation_service()


class TestSimulTransStrategy:
    """SimulTrans策略测试"""

    def setup_method(self):
        """测试前设置"""
        self.strategy = SimulTransStrategy(chunk_size=10, overlap=3)

    def test_should_translate_logic(self):
        """测试翻译判断逻辑"""
        print("\n=== 测试翻译判断逻辑 ===")

        # 测试最终文本
        assert self.strategy.should_translate("短文本", is_final=True), "最终文本应该翻译"

        # 测试长度阈值
        long_text = "这是一个很长的文本，超过了块大小限制"
        assert self.strategy.should_translate(long_text, is_final=False), "长文本应该翻译"

        # 测试句子结束符
        assert self.strategy.should_translate("短句。", is_final=False), "带句号的文本应该翻译"
        assert self.strategy.should_translate("疑问？", is_final=False), "带问号的文本应该翻译"
        assert self.strategy.should_translate("感叹！", is_final=False), "带感叹号的文本应该翻译"

        # 测试短文本
        assert not self.strategy.should_translate("短", is_final=False), "短文本不应该翻译"

        print("✅ 翻译判断逻辑测试通过")

    def test_text_preparation(self):
        """测试文本准备功能"""
        print("\n=== 测试文本准备 ===")

        # 重置策略
        self.strategy.reset()

        # 测试增量文本处理
        text1 = "你好"
        prepared1 = self.strategy.prepare_text_for_translation(text1, is_final=False)
        assert prepared1 is None, "短文本不应该准备翻译"

        text2 = "你好，世界！这是一个测试。"
        prepared2 = self.strategy.prepare_text_for_translation(text2, is_final=False)
        assert prepared2 is not None, "长文本应该准备翻译"

        # 测试最终文本
        final_text = "最终"
        prepared_final = self.strategy.prepare_text_for_translation(final_text, is_final=True)
        assert prepared_final == final_text, "最终文本应该直接翻译"

        print("✅ 文本准备测试通过")

    def test_strategy_reset(self):
        """测试策略重置"""
        print("\n=== 测试策略重置 ===")

        # 添加一些上下文
        self.strategy.previous_context = "一些上下文"
        self.strategy.translated_cache["test"] = "缓存"

        # 重置策略
        self.strategy.reset()

        assert self.strategy.previous_context == "", "上下文应该被清空"
        assert len(self.strategy.translated_cache) == 0, "缓存应该被清空"

        print("✅ 策略重置测试通过")


def run_interactive_test():
    """运行交互式测试"""
    print("🌍 翻译模块交互式测试")
    print("=" * 50)

    async def interactive_test():
        test_instance = TestTranslationModule()
        test_instance.setup_method()

        try:
            # 测试模型初始化
            print("\n1. 初始化翻译模型...")
            await test_instance.test_model_initialization()

            # 交互式翻译测试
            print("\n2. 交互式翻译测试...")
            while True:
                text = input("\n请输入要翻译的中文文本 (输入'quit'退出): ").strip()
                if text.lower() == 'quit':
                    break

                if text:
                    translated = test_instance.translator.translate_immediate(text)
                    if translated:
                        print(f"翻译结果: {translated}")
                    else:
                        print("翻译失败")

        except KeyboardInterrupt:
            print("\n测试被中断")
        finally:
            test_instance.teardown_method()

    asyncio.run(interactive_test())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="翻译模块测试")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="运行交互式测试")
    parser.add_argument("--pytest", "-p", action="store_true",
                        help="运行pytest测试")

    args = parser.parse_args()

    if args.interactive:
        run_interactive_test()
    elif args.pytest:
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