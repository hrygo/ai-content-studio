#!/usr/bin/env bash
#────────────────────────────────────────────────────────────────────────────
# ai-content-studio Skill 安装脚本
#────────────────────────────────────────────────────────────────────────────
# 功能：将当前仓库中的 ai-content-studio skill 安装到用户 Claude Code skills 目录
# 用法（从 scripts/ 目录运行）：./install.sh [--uninstall]
# 或从项目根目录运行：bash scripts/install.sh [--uninstall]
#
# 安装路径：~/.claude/skills/ai-content-studio/
# 源码路径：项目根目录（SKILL.md 所在位置）
#
# Skill Bundle 结构：
#   SKILL.md        ← 主入口
#   scripts/        ← 安装脚本、工具脚本
#   references/     ← 参考文档（配置文件说明等）
#────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# SKILL.md 和 skill bundle 在项目根目录（scripts/ 的上一级）
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
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
# 安装：复制完整 skill bundle
#────────────────────────────────────────────────────────────────────────────
install_skill() {
    if [[ ! -f "${REPO_ROOT}/SKILL.md" ]]; then
        echo "✗ 错误：找不到 ${REPO_ROOT}/SKILL.md"
        echo "  请确保在 ai-content-studio 项目根目录运行此脚本。"
        exit 1
    fi

    echo "→ 安装 ai-content-studio skill..."
    echo "  源: ${REPO_ROOT}/"
    echo "  目标: ${SKILL_DEST}/"

    # 备份已有 skill（如果存在）
    if [[ -d "$SKILL_DEST" ]]; then
        BACKUP="${HOME}/.claude/skills/${SKILL_NAME}.backup_$(date +%Y%m%d_%H%M%S)"
        echo "  ! 已存在同名 skill，备份到: ${BACKUP}"
        mv "$SKILL_DEST" "$BACKUP"
    fi

    # 复制完整 bundle
    mkdir -p "$SKILL_DEST"
    cp "${REPO_ROOT}/SKILL.md" "${SKILL_DEST}/SKILL.md"

    for subdir in scripts references tests; do
        if [[ -d "${REPO_ROOT}/${subdir}" ]]; then
            cp -r "${REPO_ROOT}/${subdir}" "${SKILL_DEST}/${subdir}"
        fi
    done

    # 标记安装来源
    touch "$INSTALL_MARKER"

    echo "✓ skill 已安装: ${SKILL_DEST}/"
    ls "${SKILL_DEST}/"
    echo ""
    echo "  重启 Claude Code 会话即可使用此 skill。"
}

#────────────────────────────────────────────────────────────────────────────
# 入口
#────────────────────────────────────────────────────────────────────────────
if [[ "$UNINSTALL" == "true" ]]; then
    uninstall_skill
else
    install_skill
fi
