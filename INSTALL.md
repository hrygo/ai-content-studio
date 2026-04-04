# AI Content Studio Skill 安装指南

> **适用对象**：Claude Code、OpenCode、OpenClaw 等 AI Agent
> **安装目标**：将 skill 安装到各 Agent 的 skills 目录，实现多 Agent 兼容

---

## 1. 概述

本 skill 遵循 **Agent Skills 通用最佳实践**，一次安装，覆盖所有主流 AI Agent。

### 1.1 支持的 Agent

| Agent | 路径类型 | 安装方式 | 备注 |
|-------|---------|---------|------|
| Claude Code | 符号链接 | `~/.claude/skills/ai-content-studio` → 主路径 | 兼容性链接 |
| OpenCode | 符号链接 | `~/.config/opencode/skills/ai-content-studio` → 主路径 | 兼容性链接 |
| OpenClaw | 符号链接 | `~/.openclaw/skills/ai-content-studio` → 主路径 | 兼容性链接 + metadata |
| Codex / Cursor / Cline | 主路径 | `~/.agents/skills/ai-content-studio/` | 原生支持 |
| **通用标准** | **主路径** | `~/.agents/skills/ai-content-studio/` | 所有 Agent 可读 |

**架构**：所有 Agent 的路径都通过符号链接指向主路径 `~/.agents/skills/ai-content-studio/`。

---

## 2. 快速安装

### 2.1 一键安装所有 Agent

```bash
# 定位 skill 源目录（当前目录即为源码仓库）
SKILL_SOURCE="$(pwd)"  # 或显式指定：/path/to/ai-content-studio

# 安装到所有支持的 Agent
cd "$SKILL_SOURCE"
bash scripts/install.sh
```

### 2.2 选择性安装

```bash
# 仅 Claude Code
bash scripts/install.sh --agent claude-code

# 仅 OpenCode
bash scripts/install.sh --agent opencode

# 仅 OpenClaw
bash scripts/install.sh --agent openclaw
```

---

## 3. Agent 特定安装

### 3.1 Claude Code

Claude Code 通过 `~/.claude/skills/` 目录识别 skill。

```bash
# 安装
bash scripts/install.sh --agent claude-code

# 验证
ls -la ~/.claude/skills/ai-content-studio
# 预期输出：符号链接指向 ~/.agents/skills/ai-content-studio

# 激活测试：在 ai-content-studio 项目目录发起任务
# "生成一段辩论播客 TTS 音频"
```

### 3.2 OpenCode

OpenCode 使用 `~/.config/opencode/skills/` 作为 skill 查找路径。

```bash
# 安装
bash scripts/install.sh --agent opencode

# 验证
ls -la ~/.config/opencode/skills/ai-content-studio
# 预期输出：符号链接指向 ~/.agents/skills/ai-content-studio

# OpenCode 应自动识别 skill（基于 SKILL.md frontmatter）
```

### 3.3 OpenClaw

OpenClaw 支持 `metadata.openclaw` 元数据格式，可声明依赖和安装器。

```bash
# 安装
bash scripts/install.sh --agent openclaw

# 验证
ls -la ~/.openclaw/skills/ai-content-studio
# 预期输出：符号链接指向 ~/.agents/skills/ai-content-studio

# OpenClaw 应读取 metadata.openclaw.requires 并提示：
#   - 系统依赖：ffmpeg（可通过 brew 安装）
#   - 环境变量：DASHSCOPE_API_KEY, MINIMAX_API_KEY
```

**ClawHub 集成**（可选）：
```bash
# 方式 1：使用 OpenClaw 原生命令（推荐）
openclaw skills install ai-content-studio

# 方式 2：使用 ClawHub CLI
npm i -g clawhub   # 先安装 CLI（如尚未安装）
clawhub install ai-content-studio
```

### 3.4 其他 Agent（Codex / Cursor / Cline）

这些 Agent 原生支持 `~/.agents/skills/` 标准路径：

```bash
# 直接使用主路径（无需符号链接）
ls ~/.agents/skills/ai-content-studio/SKILL.md
# 预期输出：skill 主入口存在
```

---

## 4. 手动安装（无脚本环境）

如果安装脚本不可用，Agent 可直接执行以下命令：

### 4.1 定义路径变量

```bash
SKILL_SOURCE="$(pwd)"                    # skill 源码仓库
SKILL_DEST="${HOME}/.agents/skills/ai-content-studio"  # 主路径
```

### 4.2 复制 skill bundle

```bash
# 创建主目录
mkdir -p "$SKILL_DEST"

# 复制核心文件
cp "${SKILL_SOURCE}/SKILL.md" "${SKILL_DEST}/"
cp "${SKILL_SOURCE}/requirements.txt" "${SKILL_DEST}/"
cp -r "${SKILL_SOURCE}/scripts/" "${SKILL_DEST}/"
cp -r "${SKILL_SOURCE}/references/" "${SKILL_DEST}/"
cp -r "${SKILL_SOURCE}/tests/" "${SKILL_DEST}/"
```

### 4.3 创建符号链接

```bash
# Claude Code
mkdir -p "${HOME}/.claude/skills/"
ln -sf "$SKILL_DEST" "${HOME}/.claude/skills/ai-content-studio"

# OpenCode
mkdir -p "${HOME}/.config/opencode/skills/"
ln -sf "$SKILL_DEST" "${HOME}/.config/opencode/skills/ai-content-studio"

# OpenClaw
mkdir -p "${HOME}/.openclaw/skills/"
ln -sf "$SKILL_DEST" "${HOME}/.openclaw/skills/ai-content-studio"
```

### 4.4 验证安装

```bash
# 检查主安装
ls -la "$SKILL_DEST/SKILL.md"

# 检查符号链接
readlink "${HOME}/.claude/skills/ai-content-studio"   # Claude Code
readlink "${HOME}/.config/opencode/skills/ai-content-studio"  # OpenCode
readlink "${HOME}/.openclaw/skills/ai-content-studio"  # OpenClaw
```

---

## 5. Git Clone 方式（版本管理）

如果 skill 已托管到 Git 仓库：

```bash
# 备份旧安装
if [[ -d "${HOME}/.agents/skills/ai-content-studio" ]]; then
    mv "${HOME}/.agents/skills/ai-content-studio" \
       "${HOME}/.agents/skills/ai-content-studio.backup_$(date +%Y%m%d_%H%M%S)"
fi

# 删除旧符号链接
rm -f "${HOME}/.claude/skills/ai-content-studio"
rm -f "${HOME}/.config/opencode/skills/ai-content-studio"
rm -f "${HOME}/.openclaw/skills/ai-content-studio"

# Clone 新版本
git clone <skill-repo-url> "${HOME}/.agents/skills/ai-content-studio"

# 重新创建符号链接
ln -sf "${HOME}/.agents/skills/ai-content-studio" "${HOME}/.claude/skills/ai-content-studio"
ln -sf "${HOME}/.agents/skills/ai-content-studio" "${HOME}/.config/opencode/skills/ai-content-studio"
ln -sf "${HOME}/.agents/skills/ai-content-studio" "${HOME}/.openclaw/skills/ai-content-studio"
```

---

## 6. 卸载

### 6.1 通用卸载

```bash
# 卸载所有 Agent 的安装
bash scripts/install.sh --uninstall
```

### 6.2 选择性卸载

```bash
# 手动删除符号链接
rm -f "${HOME}/.claude/skills/ai-content-studio"       # Claude Code
rm -f "${HOME}/.config/opencode/skills/ai-content-studio"  # OpenCode
rm -f "${HOME}/.openclaw/skills/ai-content-studio"    # OpenClaw

# 删除主安装
rm -rf "${HOME}/.agents/skills/ai-content-studio"
```

---

## 7. 故障排查

### 7.1 Skill 未激活

| 检查项 | 命令 |
|--------|------|
| 确认工作目录 | `pwd` 应在 ai-content-studio 项目根目录 |
| 检查符号链接 | `ls -la ~/.claude/skills/ai-content-studio` |
| 检查主安装 | `ls -la ~/.agents/skills/ai-content-studio/SKILL.md` |
| 重启会话 | 退出并重新进入 Agent 会话 |

### 7.2 符号链接失效

```bash
# 诊断
readlink ~/.claude/skills/ai-content-studio
# 如果输出"无此类文件或目录"，链接已断开

# 修复
bash scripts/install.sh  # 重新创建所有链接
```

### 7.3 脚本执行失败

```bash
# 检查执行权限
ls -la scripts/install.sh
# 如无执行权限：
chmod +x scripts/install.sh

# 使用调试模式运行
bash -x scripts/install.sh
```

### 7.4 备份冲突

旧版本备份占用空间，可手动清理：

```bash
rm -rf ~/.agents/skills/ai-content-studio.backup_*
rm -rf ~/.agents/skills/ai-content-studio.legacy_*
rm -rf ~/.claude/skills/ai-content-studio.backup_*
rm -rf ~/.claude/skills/ai-content-studio.legacy_*
```

---

## 8. 依赖

Skill 安装完成后，Agent 需要确保以下运行时依赖已就绪。

### 8.1 Python 环境（Agent 自动检测）

AI Agent 应在执行任务前自动检测 Python 环境，缺失时引导用户安装：

```bash
# 检测 Python 是否存在
if ! command -v python3 &>/dev/null; then
    echo "[ai-content-studio] Python 3 未安装，AI Content Studio 功能将不可用。"
    echo "安装命令："
    echo "  macOS:     brew install python"
    echo "  Linux:     sudo apt install python3 python3-pip"
    echo "  Windows:   访问 https://python.org 下载安装包"
fi

# 检测 pip 是否可用
if ! python3 -m pip --version &>/dev/null; then
    echo "[ai-content-studio] pip 未安装，Python 包将无法安装。"
    echo "  macOS:     brew install python（pip 自动包含）"
    echo "  Linux:     sudo apt install python3-pip"
fi

# 显示版本（用于诊断）
python3 --version 2>/dev/null || echo "[ai-content-studio] Python: 未安装"
python3 -m pip --version 2>/dev/null || echo "[ai-content-studio] pip: 未安装"
```

**自动安装脚本**（适用于全新环境）：
```bash
# macOS
if ! command -v python3 &>/dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew install python
fi

# Linux (Debian/Ubuntu)
if ! command -v python3 &>/dev/null; then
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi
```

### 8.2 系统依赖

| 依赖 | 说明 | 安装命令 |
|------|------|---------|
| **ffmpeg** | 音频处理引擎（必需） | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux) |

**Agent 自动检测与安装引导**：
```bash
# 检测 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "ffmpeg 未安装，音频处理将不可用！"
    echo "安装命令："
    echo "  macOS:  brew install ffmpeg"
    echo "  Linux:  sudo apt install ffmpeg"
    echo "  Docker: apt-get install ffmpeg"
    # 继续执行（仅 TTS 合成受影响，脚本仍可运行）
fi

# 显示版本（验证安装成功）
ffmpeg -version | head -n1
```

### 8.3 Python 依赖

安装 Python 包：

```bash
# 定位 requirements.txt（安装后位于主路径，源码时位于当前目录）
SKILL_DIR="${HOME}/.agents/skills/ai-content-studio"
REQUIREMENTS_FILE="${SKILL_DIR}/requirements.txt"
[[ ! -f "$REQUIREMENTS_FILE" ]] && REQUIREMENTS_FILE="$(pwd)/requirements.txt"

# 方式 1：使用 requirements.txt（推荐）
python3 -m pip install -r "$REQUIREMENTS_FILE"

# 方式 2：单独安装各依赖
python3 -m pip install requests tenacity rich cachetools

# 方式 3：使用虚拟环境（隔离环境，推荐生产环境使用）
python3 -m venv "${SKILL_DIR}/.venv"
source "${SKILL_DIR}/.venv/bin/activate"   # Linux/macOS
# .venv\Scripts\activate                    # Windows
python3 -m pip install -r "$REQUIREMENTS_FILE"
```

**Agent 批量安装参考**：
```bash
# 安装 Python 后自动装包
SKILL_DIR="${HOME}/.agents/skills/ai-content-studio"
for pkg in requests tenacity rich cachetools; do
    python3 -m pip install "$pkg" 2>/dev/null || true
done
```

**依赖说明**：

| 包 | 版本 | 用途 |
|-----|------|------|
| `requests` | >=2.31.0 | HTTP 请求（调用 TTS API） |
| `tenacity` | >=8.0.0 | 重试逻辑（API 调用的容错） |
| `rich` | >=13.0.0 | 进度条和富文本输出 |
| `cachetools` | >=5.0.0 | 结果缓存（避免重复请求） |

**常见安装问题**：

<details>
<summary><b>问题 1: 国内镜像返回 403 错误</b></summary>

某些国内 PyPI 镜像（如清华源）可能返回 HTTP 403 错误：

```
ERROR: HTTP error 403 while getting https://pypi.tuna.tsinghua.edu.cn/...
ERROR: Could not install requirement setuptools>=61.0
```

**解决方案**：使用官方 PyPI 镜像

```bash
python3 -m pip install -e "${SKILL_DIR}" \
    --break-system-packages \
    --index-url https://pypi.org/simple
```

</details>

<details>
<summary><b>问题 2: macOS 系统包保护错误</b></summary>

macOS Python 3.14+ 默认禁止系统级包安装：

```
error: externally-managed-environment
× This environment is externally managed
```

**解决方案**：添加 `--break-system-packages` 标志

```bash
python3 -m pip install -e "${SKILL_DIR}" \
    --break-system-packages
```

> **说明**：`--break-system-packages` 标志允许 pip 绕过系统包管理保护，适用于开发者环境。

</details>

<details>
<summary><b>问题 3: 自动安装失败</b></summary>

安装脚本会自动尝试两次：
1. 使用默认镜像（pip.conf 配置）
2. 回退到官方 PyPI（解决 403 问题）

如果仍然失败，请手动执行：

```bash
SKILL_DIR="${HOME}/.agents/skills/ai-content-studio"
python3 -m pip install -e "$SKILL_DIR" \
    --break-system-packages \
    --index-url https://pypi.org/simple
```

</details>

### 8.4 语音处理库（进阶）

以下库为可选，用于增强本地音频处理能力：

```bash
# 可选：音频处理增强
python3 -m pip install pydub audioop-libs  # 音频切片和转换

# 可选：波形可视化
python3 -m pip install matplotlib numpy  # 音频波形绘图
```

> **注意**：核心 TTS 功能依赖云端 API（DashScope/MiniMax），本地库为辅助工具，非必需。

### 8.5 API Key 配置

从 `~/.config/opencode/opencode.json` 自动读取：
- `provider.bailian.options.apiKey` → Qwen（DASHSCOPE_API_KEY）
- `provider.minimax.options.apiKey` → MiniMax（MINIMAX_API_KEY）

也可通过环境变量覆盖：
```bash
export DASHSCOPE_API_KEY="your-dashscope-key"
export MINIMAX_API_KEY="your-minimax-key"
```

**Agent 自动配置引导**：
```bash
# 检查 API Key 是否已配置
if [[ -z "$DASHSCOPE_API_KEY" ]] && [[ -z "$MINIMAX_API_KEY" ]]; then
    echo "[ai-content-studio] 警告：未检测到 API Key 环境变量"
    echo "TTS 功能需要至少一个 API Key，请设置："
    echo "  export DASHSCOPE_API_KEY='your-key'   # Qwen / 阿里云百炼 TTS"
    echo "  export MINIMAX_API_KEY='your-key'     # MiniMax TTS"
fi
```

---

## 9. 安装后验证

### 9.1 文件结构检查

```bash
tree -L 2 ~/.agents/skills/ai-content-studio/
# 应包含：SKILL.md, scripts/, references/, tests/
```

### 9.2 路径验证矩阵

```bash
echo "=== 路径验证 ==="
echo "主路径:     $([[ -d ~/.agents/skills/ai-content-studio ]] && echo '✓ 存在' || echo '✗ 缺失')"
echo "Claude:    $([[ -L ~/.claude/skills/ai-content-studio ]] && echo '✓ 链接' || echo '✗ 缺失')"
echo "OpenCode:  $([[ -L ~/.config/opencode/skills/ai-content-studio ]] && echo '✓ 链接' || echo '✗ 缺失')"
echo "OpenClaw:  $([[ -L ~/.openclaw/skills/ai-content-studio ]] && echo '✓ 链接' || echo '✗ 缺失')"
```

### 9.3 Skill 激活测试

在 ai-content-studio 项目目录发起任务：

```
生成一段关于 AI 发展趋势的辩论播客 TTS 音频，使用立体声和背景音乐。
```

Agent 应能：
- 自动识别 `ai-content-studio` skill
- 引用 `SKILL.md` 中的命令和架构说明
- 正确执行 TTS 合成任务

---

## 10. 更新 Skill

skill 源码更新后，重新运行安装脚本：

```bash
cd <skill-source-directory>
bash scripts/install.sh  # 自动备份旧版本
```

---

## 11. 文件结构

安装后的 skill 目录结构：

```
~/.agents/skills/ai-content-studio/
├── SKILL.md                 # Skill 主入口（含 OpenClaw metadata）
├── requirements.txt          # Python 依赖清单
├── scripts/
│   ├── install.sh           # 多 Agent 安装脚本
│   └── studio/              # TTS 引擎源码
│       ├── paths.py         # 路径配置
│       ├── studio_orchestrator.py
│       └── ...
├── references/
│   └── configs/             # 角色库配置
└── tests/
    ├── test_minimax_tts.py
    ├── test_qwen_omni_tts.py
    └── test_install.sh      # 安装脚本测试

# 符号链接
~/.claude/skills/ai-content-studio → ~/.agents/skills/ai-content-studio
~/.config/opencode/skills/ai-content-studio → ~/.agents/skills/ai-content-studio
~/.openclaw/skills/ai-content-studio → ~/.agents/skills/ai-content-studio
```
