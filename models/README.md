# 模型缓存目录

这个目录用于存储自动下载的AI模型。

## 目录结构

```
models/
├── cached_models/
│   ├── transformers/           # Hugging Face翻译模型
│   │   ├── Helsinki-NLP--opus-mt-zh-en/
│   │   ├── Helsinki-NLP--opus-mt-en-zh/
│   │   └── ...
│   ├── funasr/                # FunASR模型 (通常存在用户目录)
│   └── model_status.json     # 模型下载状态记录
├── model_manager.py          # 模型管理器
└── README.md                # 本文件
```

## 支持的模型

### FunASR模型
- `paraformer-zh-streaming`: 中文流式语音识别
- `fsmn-vad`: 语音端点检测
- `ct-punc`: 标点恢复

### 翻译模型
- `Helsinki-NLP/opus-mt-zh-en`: 中文到英文
- `Helsinki-NLP/opus-mt-en-zh`: 英文到中文
- `Helsinki-NLP/opus-mt-zh-ja`: 中文到日文
- `Helsinki-NLP/opus-mt-ja-zh`: 日文到中文
- `Helsinki-NLP/opus-mt-zh-ko`: 中文到韩文
- `Helsinki-NLP/opus-mt-ko-zh`: 韩文到中文

## 模型大小

| 模型类型 | 单个模型大小 | 说明 |
|---------|-------------|------|
| FunASR语音识别 | ~500MB | 自动下载到用户目录 |
| 翻译模型 | ~300MB | 下载到项目目录 |
| 总计 | 2-5GB | 取决于使用的语言对数量 |

## 清理模型

如果需要重新下载模型或清理空间：

```bash
# 删除所有缓存模型
rm -rf models/cached_models/*

# 删除状态文件
rm -f models/cached_models/model_status.json
```

## 注意事项

1. **首次运行**：首次使用时会自动下载所需模型
2. **网络连接**：下载过程需要稳定的网络连接
3. **存储空间**：确保有足够的磁盘空间（建议5GB+）
4. **权限**：确保程序有写入权限

## 手动管理

```python
from models.model_manager import model_manager

# 检查模型状态
info = model_manager.get_model_info()
print(info)

# 手动下载模型
success = model_manager.download_translation_model("Helsinki-NLP/opus-mt-zh-en")

# 清空缓存
model_manager.clear_cache()
```