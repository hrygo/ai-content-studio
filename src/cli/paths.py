"""
paths.py - AI Content Studio 共享路径配置
统一管理项目路径，支持从 src/cli/ 子目录访问项目根目录资源
"""
from pathlib import Path

# 脚本所在目录（src/cli/）
SCRIPT_DIR = Path(__file__).parent

# 项目根目录（ai-content-studio/）- 向上两级
REPO_ROOT = SCRIPT_DIR.parent.parent

# 运行时目录
ASSETS_DIR = REPO_ROOT / "assets"
OUTPUTS_DIR = ASSETS_DIR / "outputs"
WORK_DIR = ASSETS_DIR / "work"
WORK_QWEN_DIR = ASSETS_DIR / "work_qwen"
WORK_TTS_DIR = ASSETS_DIR / "work_tts"

# 配置文件目录
CONFIGS_DIR = REPO_ROOT / "references" / "configs"

# 默认角色库路径
DEFAULT_ROLES = CONFIGS_DIR / "studio_roles.json"
DEFAULT_QWEN_VOICES = CONFIGS_DIR / "qwen_voices.json"

# 确保运行时目录存在
for _d in [OUTPUTS_DIR, WORK_DIR, WORK_QWEN_DIR, WORK_TTS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
