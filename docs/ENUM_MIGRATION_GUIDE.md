# 枚举类型迁移指南

## Enum Migration Guide

**版本**: v1.1.0
**日期**: 2026-04-02
**状态**: Draft

---

## 概述

本指南帮助你将现有代码从字符串常量迁移到类型安全的枚举（`core.enums`）。

迁移分为 **3 个阶段**，降低破坏性变更的风险。

---

## Phase 1: 韺础迁移（v1.1.0）

**目标**: 引入枚举，保持向后兼容

### Step 1.1: 更新导入

```python
# Before
from src.core.tts_engines.qwen_tts import QwenTTSEngine

# After
from src.core.tts_engines.qwen_tts import QwenTTSEngine
from src.core.enums import LanguageCode,  # 新增
```

### Step 1.2: 使用枚举常量
```python
# Before
engine.synthesize(
    text="你好",
    language="zh",  # 字符串硬编码
    voice="cherry"
)

# After (推荐方式)
engine.synthesize(
    text="你好",
    language=LanguageCode.ZH,  # 类型安全
    voice=QwenVoiceID.CHERRY
)

# After (向后兼容方式 - 仍然支持字符串)
engine.synthesize(
    text="你好",
    language="zh",  # 字符串仍然有效（通过 from_string 转换）
    voice="cherry"
)
```

### Step 1.3: 配置文件无需更改
```json
// config.json 保持不变
{
    "voice": "cherry",
    "language": "zh"
}
```

配置加载器会自动转换：
```python
# services/config.py
voice = QwenVoiceID.from_string(config["voice"])
language = LanguageCode.from_string(config["language"])
```

### 验证迁移
```bash
# 运行测试
pytest tests/test_qwen_tts.py

# 检查日志（应无警告）
python src/cli/qwen_tts_tool.py --text "测试" --voice cherry
```

---

## Phase 2: 配置升级（v1.2.0）

**目标**: 在配置中使用枚举值

### Step 2.1: 更新 JSON 配置（可选）
```json
// Before
{
    "default_engine": "minimax",
    "voice": "cherry"
}

// After (推荐)
{
    "default_engine": "minimax",
    "voice": "cherry",  // 保持字符串格式也可以
    "_comment": "推荐使用字符串格式以保证人类可读性"
}
```

**注意**: JSON 配置保持字符串格式更易读，加载时再转换为枚举。

### Step 2.2: 添加配置验证
```python
# services/config.py
from pydantic import BaseModel, validator
from src.core.enums import LanguageCode

class RoleConfig(BaseModel):
    voice: str
    emotion: str = "neutral"
    language: str = "Auto"

    @validator("emotion")
    def validate_emotion(cls, v):
        """验证情感值是否有效"""
        from src.core.enums import EmotionType
        try:
            EmotionType.from_string(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid emotion: {v}")

    @validator("language")
    def validate_language(cls, v):
        """验证语言代码是否有效"""
        try:
            LanguageCode.from_string(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid language: {v}")
```

### 验证配置
```bash
# 测试配置加载
python -c "
from src.services.config import ConfigManager
cfg = ConfigManager('config.example.json')
print(cfg.engines['qwen'].voice)  # 应该是 QwenVoiceID 枚举
"
```

---

## Phase 3: 清理废弃代码（v2.0.0）

**目标**: 移除字符串支持， 仅使用枚举

### Step 3.1: 添加废弃警告
```python
# core/tts_engines/qwen_tts.py
import warnings

def synthesize(
    self,
    text: str,
    output_file: str,
    voice: Union[str, QwenVoiceID],  # 同时支持两种类型
    language: Union[str, LanguageCode] = LanguageCode.AUTO,
) -> bool:
    # 检查是否使用了字符串
    if isinstance(voice, str):
        warnings.warn(
            "String voice IDs are deprecated, use QwenVoiceID enum. "
            "Example: voice=QwenVoiceID.CHERRY",
            DeprecationWarning,
            stacklevel=2
        )
        voice = QwenVoiceID.from_string(voice)

    if isinstance(language, str):
        warnings.warn(
            "String language codes are deprecated, use LanguageCode enum. "
            "Example: language=LanguageCode.ZH",
            DeprecationWarning,
            stacklevel=2
        )
        language = LanguageCode.from_string(language)

    # ... rest of implementation
```

### Step 3.2: 更新所有调用方
```python
# Before
engine.synthesize(text, voice="cherry", language="zh")

# After
engine.synthesize(
    text,
    voice=QwenVoiceID.CHERRY,
    language=LanguageCode.ZH
)
```

### Step 3.3: v2.0.0 移除字符串支持
```python
# core/tts_engines/qwen_tts.py
def synthesize(
    self,
    text: str,
    output_file: str,
    voice: QwenVoiceID,  # 仅支持枚举
    language: LanguageCode = LanguageCode.AUTO,
) -> bool:
    # 直接使用枚举，无需转换
    ...
```

---

## 常见迁移场景

### 场景 1: TTS 引擎调用
```python
# core/tts_engines/qwen_tts.py

# Before
def synthesize(self, text: str, voice: str = "cherry", language: str = "Auto"):
    if language not in ["Auto", "zh", "en"]:
        raise ValueError(f"Unsupported language: {language}")
    # ...

# After (Phase 1)
from src.core.enums import QwenVoiceID, LanguageCode

def synthesize(
    self,
    text: str,
    voice: Union[str, QwenVoiceID] = QwenVoiceID.CHERRY,
    language: Union[str, LanguageCode] = LanguageCode.AUTO
):
    # 自动转换
    if isinstance(voice, str):
        voice = QwenVoiceID.from_string(voice)
    if isinstance(language, str):
        language = LanguageCode.from_string(language)
    # ...
```

### 场景 2: CLI 参数解析
```python
# src/cli/qwen_tts_tool.py

# Before
import click

@click.option("--language", default="Auto", help="Language code")
@click.option("--voice", default="cherry", help="Voice ID")
def main(language: str, voice: str):
    engine.synthesize(text, voice=voice, language=language)

# After (Phase 1)
import click
from src.core.enums import LanguageCode, QwenVoiceID

@click.option(
    "--language",
    default=LanguageCode.AUTO,
    type=click.Choice([v.value for v in LanguageCode]),
    help="Language code"
)
@click.option(
    "--voice",
    default=QwenVoiceID.CHERRY,
    type=click.Choice([v.value for v in QwenVoiceID]),
    help="Voice ID"
)
def main(language: str, voice: str):
    # Click 传递的是字符串，自动转换为枚举
    lang_enum = LanguageCode.from_string(language)
    voice_enum = QwenVoiceID.from_string(voice)
    engine.synthesize(text, voice=voice_enum, language=lang_enum)
```

### 场景 3: JSON 配置加载
```python
# services/config.py

# Before
with open("config.json") as f:
    config = json.load(f)
    voice = config["voice"]  # 字符串 "cherry"

# After (Phase 1)
from src.core.enums import QwenVoiceID

with open("config.json") as f:
    config = json.load(f)
    voice = QwenVoiceID.from_string(config["voice"])  # 枚举 QwenVoiceID.CHERRY
```

---

## 测试策略

### 单元测试
```python
# tests/test_enums.py
import pytest
from src.core.enums import LanguageCode, EmotionType, QwenVoiceID

def test_language_code_from_string():
    assert LanguageCode.from_string("zh") == LanguageCode.ZH
    assert LanguageCode.from_string("ZH") == LanguageCode.ZH  # case-insensitive
    assert LanguageCode.from_string("invalid") == LanguageCode.AUTO  # fallback

def test_emotion_type_from_string():
    assert EmotionType.from_string("happy") == EmotionType.HAPPY
    assert EmotionType.from_string("  calm  ") == EmotionType.CALM  # strip whitespace
    assert EmotionType.from_string("NEUTRAL") == EmotionType.NEUTRAL

def test_enum_string_equality():
    """测试枚举与字符串的比较（向后兼容）"""
    assert LanguageCode.ZH == "zh"
    assert EmotionType.HAPPY == "happy"
    assert QwenVoiceID.CHERRY == "cherry"

def test_config_loading():
    """测试配置加载后的枚举转换"""
    config = {"voice": "cherry", "language": "zh"}
    voice = QwenVoiceID.from_string(config["voice"])
    language = LanguageCode.from_string(config["language"])
    assert voice == QwenVoiceID.CHERRY
    assert language == LanguageCode.ZH
```

### 集成测试
```python
# tests/test_qwen_tts_integration.py
def test_synthesis_with_enum():
    """测试使用枚举的 TTS 合成"""
    engine = QwenTTSEngine(api_key="test_key")

    # 使用枚举
    success = engine.synthesize(
        text="测试文本",
        output_file="test.wav",
        voice=QwenVoiceID.CHERRY,
        language=LanguageCode.ZH
    )
    assert success

def test_synthesis_with_string_backward_compat():
    """测试向后兼容字符串输入"""
    engine = QwenTTSEngine(api_key="test_key")

    # 使用字符串（向后兼容）
    success = engine.synthesize(
        text="测试文本",
        output_file="test.wav",
        voice="cherry",  # 字符串仍然有效
        language="zh"
    )
    assert success
```

---

## 故障排查

### 问题 1: 枚举值无法匹配
**症状**: `LanguageCode.from_string("zh")` 返回 `AUTO`

**解决**:
```python
# 检查是否正确导入
from src.core.enums import LanguageCode

# 检查值是否正确
print([v.value for v in LanguageCode])  # 应该包含 "zh"

# 如果没有，检查拼写
assert LanguageCode.ZH.value == "zh"
```

### 问题 2: JSON 序列化问题
**症状**: 保存枚举到 JSON 时出错

**解决**:
```python
# 枚举继承 str，可以直接序列化
import json
from src.core.enums import QwenVoiceID

voice = QwenVoiceID.CHERRY
json_str = json.dumps({"voice": voice})  # 自动使用 voice.value
print(json_str)  # {"voice": "cherry"}

# 或者显式转换
config = {"voice": voice.value}  # "cherry"
```

### 问题 3: 类型检查错误
**症状**: mypy 报错 `Incompatible types`

**解决**:
```python
# Before
def process(voice: str):
    ...

process(QwenVoiceID.CHERRY)  # mypy 错误

# After
from typing import Union
from src.core.enums import QwenVoiceID

def process(voice: Union[str, QwenVoiceID]):
    if isinstance(voice, QwenVoiceID):
        voice_str = voice.value
    else:
        voice_str = voice
    ...

process(QwenVoiceID.CHERRY)  # OK
```

---

## 检查清单

### Phase 1 检查
- [ ] 所有 TTS 引擎更新为支持枚举
- [ ] 配置加载器添加 `from_string` 转换
- [ ] 添加单元测试覆盖枚举转换
- [ ] 文档更新（API Reference）

### Phase 2 检查
- [ ] CLI 工具添加枚举选项验证
- [ ] Pydantic 模型添加枚举验证
- [ ] 集成测试通过
- [ ] 更新 CHANGELOG.md

### Phase 3 检查
- [ ] 移除所有字符串类型提示（`Union[str, Enum]` -> `Enum`）
- [ ] 添加 DeprecationWarning（v1.2.0）
- [ ] 更新所有示例和文档
- [ ] 发布 v2.0.0 迁移指南

---

## 参考资料

- **设计文档**: `docs/STRINGLY_TYPED_CODE_ANALYSIS.md`
- **枚举实现**: `src/core/enums.py`
- **使用示例**: `examples/enums_usage_demo.py`
- **API 文档**: `docs/API_REFERENCE.md` (待创建)

---

## 需要帮助？

如果在迁移过程中遇到问题：
1. 检查 `src/core/enums.py` 中的 `from_string` 方法实现
2. 查看测试用例 `tests/test_enums.py`
3. 参考示例 `examples/enums_usage_demo.py`

**迁移支持**: 提交 Issue 或联系开发团队
