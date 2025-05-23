"""
实时语音翻译系统安装脚本
=======================
自动化安装和配置系统环境
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path


class SystemSetup:
    """系统安装和配置管理器"""

    def __init__(self):
        self.platform = platform.system().lower()
        self.python_version = sys.version_info
        self.project_root = Path(__file__).parent
        self.requirements_file = self.project_root / "requirements.txt"

    def check_python_version(self):
        """检查Python版本"""
        print("🐍 检查Python版本...")

        if self.python_version < (3, 7):
            print("❌ 错误: 需要Python 3.7或更高版本")
            print(f"   当前版本: {sys.version}")
            return False

        print(f"✅ Python版本: {sys.version}")
        return True

    def check_system_requirements(self):
        """检查系统要求"""
        print("🖥️  检查系统要求...")

        # 检查操作系统
        print(f"操作系统: {platform.platform()}")

        # 检查音频支持
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]

            if len(input_devices) == 0:
                print("⚠️  警告: 未检测到音频输入设备")
                return False

            print(f"✅ 检测到 {len(input_devices)} 个音频输入设备")

        except ImportError:
            print("⚠️  警告: sounddevice未安装，将在安装依赖时安装")
        except Exception as e:
            print(f"⚠️  音频设备检查失败: {e}")

        return True

    def install_dependencies(self, upgrade=False):
        """安装Python依赖"""
        print("📦 安装Python依赖...")

        if not self.requirements_file.exists():
            print("❌ 错误: requirements.txt文件不存在")
            return False

        try:
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)]
            if upgrade:
                cmd.append("--upgrade")

            print(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            print("✅ 依赖安装完成")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            print(f"错误输出: {e.stderr}")
            return False

    def install_system_dependencies(self):
        """安装系统级依赖"""
        print("🔧 检查系统级依赖...")

        if self.platform == "linux":
            return self._install_linux_dependencies()
        elif self.platform == "darwin":  # macOS
            return self._install_macos_dependencies()
        elif self.platform == "windows":
            return self._install_windows_dependencies()
        else:
            print("⚠️  不支持的操作系统")
            return False

    def _install_linux_dependencies(self):
        """安装Linux系统依赖"""
        print("🐧 检查Linux系统依赖...")

        # 检查音频库
        required_packages = [
            "portaudio19-dev",
            "python3-pyaudio",
            "espeak",
            "espeak-data",
            "libespeak1"
        ]

        try:
            # 检查包管理器
            if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
                print("使用apt包管理器...")
                for package in required_packages:
                    try:
                        subprocess.run(["dpkg", "-l", package],
                                       check=True, capture_output=True)
                        print(f"✅ {package} 已安装")
                    except subprocess.CalledProcessError:
                        print(f"📦 安装 {package}...")
                        subprocess.run(["sudo", "apt", "install", "-y", package],
                                       check=True)
            else:
                print("⚠️  未检测到apt包管理器，请手动安装音频库")

        except Exception as e:
            print(f"⚠️  系统依赖安装可能不完整: {e}")

        return True

    def _install_macos_dependencies(self):
        """安装macOS系统依赖"""
        print("🍎 检查macOS系统依赖...")

        try:
            # 检查Homebrew
            if subprocess.run(["which", "brew"], capture_output=True).returncode == 0:
                print("使用Homebrew...")
                packages = ["portaudio", "espeak"]
                for package in packages:
                    try:
                        subprocess.run(["brew", "list", package],
                                       check=True, capture_output=True)
                        print(f"✅ {package} 已安装")
                    except subprocess.CalledProcessError:
                        print(f"📦 安装 {package}...")
                        subprocess.run(["brew", "install", package], check=True)
            else:
                print("⚠️  建议安装Homebrew来管理系统依赖")
                print(
                    "   安装命令: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")

        except Exception as e:
            print(f"⚠️  系统依赖安装可能不完整: {e}")

        return True

    def _install_windows_dependencies(self):
        """安装Windows系统依赖"""
        print("🪟 检查Windows系统依赖...")

        print("✅ Windows通常不需要额外的系统依赖")
        print("💡 如果遇到音频问题，请确保安装了Microsoft Visual C++ Redistributable")

        return True

    def create_directories(self):
        """创建必要的目录"""
        print("📁 创建项目目录...")

        directories = [
            "logs",
            "models/cached_models",
            "config",
            "data/recordings",
            "data/exports"
        ]

        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {directory}")

        return True

    def create_config_files(self):
        """创建配置文件"""
        print("⚙️  创建配置文件...")

        # 创建示例配置文件
        config_file = self.project_root / "config" / "user_config.yaml"

        if not config_file.exists():
            config_content = """# 实时语音翻译系统用户配置文件
# ===================================

# 音频配置
audio:
  sample_rate: 16000
  use_vad: true
  use_punctuation: true
  max_segment_duration_seconds: 7.0

# 翻译配置  
translation:
  source_language: "zh"
  target_language: "en"
  chunk_size: 128
  max_length: 512

# TTS配置
tts:
  voice: "en-US-AriaNeural"
  rate: "+0%"
  pitch: "+0Hz"
  volume: "+0%"

# 日志配置
logging:
  level: "INFO"
  enable_console: true
  enable_file: true
  max_file_size: 10485760  # 10MB

# 性能配置
performance:
  enable_gpu: true
  batch_size: 1
  num_threads: 4
"""

            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)

            print(f"✅ 创建配置文件: {config_file}")

        return True

    def test_installation(self):
        """测试安装结果"""
        print("🧪 测试安装结果...")

        # 测试导入主要模块
        test_imports = [
            ("torch", "PyTorch"),
            ("transformers", "Transformers"),
            ("funasr", "FunASR"),
            ("sounddevice", "SoundDevice"),
            ("edge_tts", "Edge-TTS"),
            ("numpy", "NumPy"),
            ("pygame", "PyGame")
        ]

        failed_imports = []

        for module, name in test_imports:
            try:
                __import__(module)
                print(f"✅ {name} 导入成功")
            except ImportError as e:
                print(f"❌ {name} 导入失败: {e}")
                failed_imports.append(name)

        if failed_imports:
            print(f"\n⚠️  以下模块导入失败: {', '.join(failed_imports)}")
            print("请检查安装或重新运行安装程序")
            return False

        # 测试音频设备
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]

            if len(input_devices) > 0:
                print(f"✅ 音频设备测试通过 ({len(input_devices)} 个输入设备)")
            else:
                print("⚠️  未检测到音频输入设备")

        except Exception as e:
            print(f"⚠️  音频设备测试失败: {e}")

        print("\n🎉 安装测试完成！")
        return len(failed_imports) == 0

    def run_setup(self, upgrade_deps=False, skip_system_deps=False):
        """运行完整安装流程"""
        print("🚀 开始安装实时语音翻译系统...")
        print("=" * 50)

        # 检查Python版本
        if not self.check_python_version():
            return False

        # 检查系统要求
        if not self.check_system_requirements():
            print("⚠️  系统要求检查失败，但将继续安装...")

        # 创建目录
        if not self.create_directories():
            print("❌ 目录创建失败")
            return False

        # 安装系统依赖
        if not skip_system_deps:
            if not self.install_system_dependencies():
                print("⚠️  系统依赖安装可能不完整，但将继续安装...")

        # 安装Python依赖
        if not self.install_dependencies(upgrade=upgrade_deps):
            print("❌ Python依赖安装失败")
            return False

        # 创建配置文件
        if not self.create_config_files():
            print("❌ 配置文件创建失败")
            return False

        # 测试安装
        if not self.test_installation():
            print("❌ 安装测试失败")
            return False

        print("\n" + "=" * 50)
        print("🎉 安装完成！")
        print("\n📖 使用方法:")
        print("   python main.py")
        print("\n📚 更多信息请查看 README.md")

        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="实时语音翻译系统安装脚本")
    parser.add_argument("--upgrade", "-u", action="store_true",
                        help="升级已安装的依赖包")
    parser.add_argument("--skip-system-deps", action="store_true",
                        help="跳过系统级依赖安装")
    parser.add_argument("--test-only", action="store_true",
                        help="仅运行安装测试")

    args = parser.parse_args()

    setup = SystemSetup()

    if args.test_only:
        print("🧪 运行安装测试...")
        success = setup.test_installation()
        sys.exit(0 if success else 1)

    try:
        success = setup.run_setup(
            upgrade_deps=args.upgrade,
            skip_system_deps=args.skip_system_deps
        )
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⏹️  安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 安装过程出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()