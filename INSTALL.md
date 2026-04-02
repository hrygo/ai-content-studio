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
# 如果使用 ClawHub 管理 skill，可从 ClawHub 安装
claw skill add ai-content-studio
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

Skill 安装完成后，需要确保运行时依赖已就绪：

### 8.1 系统依赖

| 依赖 | 说明 | 安装命令 |
|------|------|---------|
| **ffmpeg** | 音频处理引擎（必需） | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux) |

OpenClaw 可通过 metadata 自动检测缺失依赖。

### 8.2 Python 依赖

```bash
pip install -r requirements.txt
```

### 8.3 API Key 配置

从 `~/.config/opencode/opencode.json` 自动读取：
- `provider.bailian` → Qwen（DASHSCOPE_API_KEY）
- `provider.minimax` → MiniMax（MINIMAX_API_KEY）

也可通过环境变量覆盖：
```bash
export DASHSCOPE_API_KEY="your-dashscope-key"
export MINIMAX_API_KEY="your-minimax-key"
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
