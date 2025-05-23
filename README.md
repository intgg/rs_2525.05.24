# 🎙️ 实时语音翻译系统

基于 FunASR + Transformers + Edge-TTS 的高性能实时语音翻译系统，支持多语言语音识别、机器翻译和语音合成。

## ✨ 主要特性

- 🎤 **实时语音识别**: 基于 FunASR 的流式语音识别，支持 VAD 和标点恢复
- 🌍 **多语言翻译**: 基于 Hugging Face Transformers 的机器翻译，支持多语言对
- 🔊 **语音合成**: 基于 Edge-TTS 的高质量语音合成，支持多种音色
- ⚡ **SimulTrans 策略**: 实现同步翻译，减少延迟
- 🔧 **模块化设计**: 清晰的模块划分，易于维护和扩展
- 📦 **自动模型管理**: 首次运行自动下载并缓存模型
- 📊 **性能监控**: 完整的日志系统和性能统计
- 🎯 **易于使用**: 交互式命令行界面

## 🏗️ 系统架构

```
实时语音翻译系统
├── 音频捕获模块 (FunASR)
│   ├── VAD 语音端点检测
│   ├── 流式语音识别
│   └── 标点恢复
├── 翻译模块 (Transformers)
│   ├── SimulTrans 策略
│   ├── 多语言支持
│   └── 缓存优化
├── 语音合成模块 (Edge-TTS)
│   ├── 多音色支持
│   ├── 实时播放
│   └── 队列管理
└── 系统管道协调器
    ├── 模块协调
    ├── 错误处理
    └── 性能监控
```

## 📋 支持的语言

| 语言 | 代码 | 识别 | 翻译 | 语音合成 |
|------|------|------|------|----------|
| 中文 | zh | ✅ | ✅ | ✅ |
| 英语 | en | ❌ | ✅ | ✅ |
| 日语 | ja | ❌ | ✅ | ✅ |
| 韩语 | ko | ❌ | ✅ | ✅ |
| 法语 | fr | ❌ | ✅ | ✅ |
| 德语 | de | ❌ | ✅ | ✅ |
| 西班牙语 | es | ❌ | ✅ | ✅ |
| 俄语 | ru | ❌ | ✅ | ✅ |

*注：目前语音识别主要支持中文，其他语言的语音识别功能可通过更换 FunASR 模型来支持*

## 🚀 快速开始

### 环境要求

- Python 3.7+
- 系统支持麦克风录音
- 网络连接（用于下载模型和 Edge-TTS）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-repo/real-time-translator.git
cd real-time-translator
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行系统**
```bash
python main.py
```

### 首次运行

首次运行时，系统会自动下载需要的模型：

1. **FunASR 模型** (约 500MB)
   - paraformer-zh-streaming (语音识别)
   - fsmn-vad (语音端点检测)
   - ct-punc (标点恢复)

2. **翻译模型** (每个约 300MB)
   - 根据选择的语言对自动下载
   - 模型缓存在 `./models/cached_models/` 目录

3. **Edge-TTS**
   - 无需下载，在线使用

## 🎯 使用方法

### 基本使用

1. **启动程序**
```bash
python main.py
```

2. **选择语言对**
   - 源语言：您要说的语言
   - 目标语言：要翻译成的语言

3. **开始翻译**
   - 选择"开始翻译"
   - 对着麦克风说话
   - 系统自动识别、翻译并播放

### 高级功能

#### 1. 命令行参数
```bash
# 指定配置文件
python main.py --config config.yaml

# 指定日志级别
python main.py --log-level DEBUG

# 禁用VAD
python main.py --no-vad

# 禁用标点恢复
python main.py --no-punc
```

#### 2. 编程接口
```python
from modules.pipeline import RealTimeTranslationPipeline

# 创建管道
pipeline = RealTimeTranslationPipeline()

# 初始化
await pipeline.initialize("zh", "en")

# 启动翻译
pipeline.start_translation()

# 停止翻译
pipeline.stop_translation()
```

## 🔧 配置说明

### 音频配置
```python
# config/settings.py
@dataclass
class AudioConfig:
    sample_rate: int = 16000  # 采样率
    use_vad: bool = True      # 启用VAD
    use_punctuation: bool = True  # 启用标点恢复
    max_segment_duration_seconds: float = 7.0  # 最大片段时长
```

### 翻译配置
```python
@dataclass
class TranslationConfig:
    source_language: str = "zh"  # 源语言
    target_language: str = "en"  # 目标语言
    chunk_size: int = 128       # SimulTrans块大小
    max_length: int = 512       # 最大翻译长度
```

### TTS配置
```python
@dataclass
class TTSConfig:
    voice: str = "en-US-AriaNeural"  # 音色
    rate: str = "+0%"                # 语速
    pitch: str = "+0Hz"              # 音调
    volume: str = "+0%"              # 音量
```

## 🧪 测试

### 运行所有测试
```bash
pytest tests/ -v
```

### 单独测试模块
```bash
# 测试音频捕获
python tests/test_audio_capture.py --interactive

# 测试翻译功能
python tests/test_translator.py --interactive

# 测试TTS功能
python tests/test_text_to_speech.py --interactive
```

### 性能测试
```bash
python tests/performance_test.py
```

## 📊 性能指标

### 延迟指标
- **音频采集延迟**: < 100ms
- **语音识别延迟**: 200-500ms
- **翻译延迟**: 100-300ms
- **语音合成延迟**: 200-400ms
- **总端到端延迟**: < 1.5s

### 资源占用
- **内存使用**: 2-4GB (包含模型)
- **CPU使用**: 10-30% (取决于模型大小)
- **磁盘空间**: 2-5GB (模型缓存)

## 🐛 故障排除

### 常见问题

#### 1. 音频设备问题
```bash
# 检查音频设备
python -c "
from utils.audio_utils import AudioDeviceManager
devices = AudioDeviceManager.list_audio_devices()
for device in devices:
    if device['max_input_channels'] > 0:
        print(f'输入设备: {device}')
"
```

#### 2. 模型下载失败
```bash
# 清除模型缓存重新下载
rm -rf ./models/cached_models/
python main.py
```

#### 3. 内存不足
```bash
# 使用较小的模型
export FUNASR_MODEL_SIZE=small
python main.py
```

#### 4. 网络连接问题
```bash
# 使用代理
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
python main.py
```

### 调试模式
```bash
# 启用详细日志
python main.py --log-level DEBUG

# 查看日志文件
tail -f logs/translation_system.log
```

## 🔌 扩展开发

### 添加新的翻译模型
```python
# config/settings.py
class ModelConfig:
    def __post_init__(self):
        self.translation_models.update({
            "zh-fr": "Helsinki-NLP/opus-mt-zh-fr",
            "fr-zh": "Helsinki-NLP/opus-mt-fr-zh",
        })
```

### 自定义语音识别模型
```python
# modules/audio_capture.py
class AudioCaptureModule:
    def __init__(self, custom_asr_model="your-custom-model"):
        self.model_config.asr_model = custom_asr_model
```

### 添加新的回调处理
```python
def my_callback(text, is_final):
    if is_final:
        # 处理最终识别结果
        save_to_database(text)

pipeline.add_text_callback(my_callback)
```

## 📁 项目结构

```
real_time_translator/
├── main.py                     # 主程序入口
├── quick_start.py              # 快速启动脚本
├── setup.py                    # 安装配置脚本
├── config/
│   ├── __init__.py
│   └── settings.py             # 配置管理
├── models/
│   ├── __init__.py
│   ├── model_manager.py        # 模型下载与管理
│   └── cached_models/          # 本地模型缓存
├── modules/
│   ├── __init__.py
│   ├── audio_capture.py        # 音频捕获与识别
│   ├── translator.py           # 实时翻译
│   ├── text_to_speech.py       # 语音合成
│   └── pipeline.py             # 系统管道协调器
├── utils/
│   ├── __init__.py
│   ├── audio_utils.py          # 音频工具
│   └── logger.py               # 日志系统
├── tests/
│   ├── __init__.py
│   ├── test_audio_capture.py   # 音频测试
│   ├── test_translator.py      # 翻译测试
│   └── test_text_to_speech.py  # TTS测试
├── logs/                       # 日志文件目录
├── requirements.txt            # 依赖列表
└── README.md                   # 项目说明
```

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发规范

- 遵循 PEP 8 代码风格
- 添加适当的类型提示
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FunASR](https://github.com/alibaba-damo-academy/FunASR) - 语音识别
- [Hugging Face Transformers](https://github.com/huggingface/transformers) - 机器翻译
- [Edge-TTS](https://github.com/rany2/edge-tts) - 语音合成
- [PyAudio](https://pypi.org/project/PyAudio/) - 音频处理

## 📮 联系方式

- 项目主页: https://github.com/your-repo/real-time-translator
- 问题反馈: https://github.com/your-repo/real-time-translator/issues
- 邮箱: your-email@example.com

## 🔄 更新日志

### v1.0.0 (2024-01-XX)
- ✨ 初始版本发布
- 🎤 实现基于 FunASR 的实时语音识别
- 🌍 集成 Transformers 多语言翻译
- 🔊 集成 Edge-TTS 语音合成
- 📦 自动模型下载和管理
- 🎯 交互式命令行界面

---

⭐ 如果这个项目对您有帮助，请给我们一个 Star！