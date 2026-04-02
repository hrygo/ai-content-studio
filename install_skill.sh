#!/usr/bin/env bash
#────────────────────────────────────────────────────────────────────────────
# ai-content-studio Skill 安装脚本
#────────────────────────────────────────────────────────────────────────────
# 功能：将当前仓库中的 ai-content-studio skill 安装到用户 Claude Code skills 目录
# 用法：./install.sh [--uninstall]
#
# 安装路径：~/.claude/skills/ai-content-studio/
# 源码路径：当前仓库根目录（SKILL.md 所在位置）
#────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="ai-content-studio"
SKILL_DEST="${HOME}/.claude/skills/${SKILL_NAME}"
INSTALL_MARKER="${SKILL_DEST}/.installed_from_ai_content_studio_repo"

# 解析参数
UNINSTALL=false
if [[ "${1:-}" == "--uninstall" ]]; then
    UNINSTALL=true
fi

#────────────────────────────────────────────────────────────────────────────
# 卸载
#────────────────────────────────────────────────────────────────────────────
uninstall_skill() {
    if [[ -d "$SKILL_DEST" ]]; then
        echo "→ 卸载 skill: ${SKILL_DEST}"
        rm -rf "$SKILL_DEST"
        echo "✓ 已移除 ${SKILL_DEST}"
    else
        echo "→ 未找到已安装的 skill: ${SKILL_DEST}"
    fi
}

#────────────────────────────────────────────────────────────────────────────
# 安装
#────────────────────────────────────────────────────────────────────────────
install_skill() {
    # 源码检查：SKILL.md 必须在脚本同目录
    if [[ ! -f "${SCRIPT_DIR}/SKILL.md" ]]; then
        echo "✗ 错误：找不到 ${SCRIPT_DIR}/SKILL.md"
        echo "  请确保在 ai-content-studio 项目根目录运行此脚本。"
        exit 1
    fi

    echo "→ 安装 ai-content-studio skill..."
    echo "  源: ${SCRIPT_DIR}/SKILL.md"
    echo "  目标: ${SKILL_DEST}/"

    # 备份已有 skill（如果存在）
    if [[ -d "$SKILL_DEST" ]]; then
        BACKUP="${HOME}/.claude/skills/${SKILL_NAME}.backup_$(date +%Y%m%d_%H%M%S)"
        echo "  ! 已存在同名 skill，备份到: ${BACKUP}"
        mv "$SKILL_DEST" "$BACKUP"
    fi

    # 创建目标目录并复制
    mkdir -p "$SKILL_DEST"
    cp "${SCRIPT_DIR}/SKILL.md" "${SKILL_DEST}/SKILL.md"

    # 标记安装来源（用于 uninstall 检测和重装）
    touch "$INSTALL_MARKER"

    echo "✓ skill 已安装: ${SKILL_DEST}/SKILL.md"
    echo ""
    echo "  重启 Claude Code 会话即可使用此 skill。"
    echo "  安装后 Claude Code 会话中遇到任何 AI Content Studio 相关任务，"
    echo "  agent 会自动激活此 skill。"
}

#────────────────────────────────────────────────────────────────────────────
# 入口
#────────────────────────────────────────────────────────────────────────────
if [[ "$UNINSTALL" == "true" ]]; then
    uninstall_skill
else
    install_skill
fi
