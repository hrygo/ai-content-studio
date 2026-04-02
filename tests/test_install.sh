#!/usr/bin/env bash
#────────────────────────────────────────────────────────────────────────────
# ai-content-studio 安装脚本集成测试
#────────────────────────────────────────────────────────────────────────────
# 测试覆盖：
#   1. --help 参数输出
#   2. 语法检查
#   3. --agent claude-code 仅创建 Claude 链接
#   4. --uninstall 完全卸载
#   5. 重复安装不报错，自动备份
#   6. 全量安装（--agent all）4 个路径正确
#────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_SCRIPT="${REPO_ROOT}/scripts/install.sh"

# 测试输出颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

#────────────────────────────────────────────────────────────────────────────
# 测试工具函数
#────────────────────────────────────────────────────────────────────────────
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++)) || true
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++)) || true
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

section() {
    echo ""
    echo "═══════════════════════════════════════════════"
    echo " $1"
    echo "═══════════════════════════════════════════════"
}

#────────────────────────────────────────────────────────────────────────────
# 前置清理
#────────────────────────────────────────────────────────────────────────────
cleanup_all() {
    info "清理所有测试安装..."

    for path in \
        "${HOME}/.agents/skills/ai-content-studio" \
        "${HOME}/.claude/skills/ai-content-studio" \
        "${HOME}/.config/opencode/skills/ai-content-studio" \
        "${HOME}/.openclaw/skills/ai-content-studio"; do

        if [[ -L "$path" ]] || [[ -d "$path" ]]; then
            rm -rf "$path"
        fi
    done

    # 清理备份
    rm -rf "${HOME}/.agents/skills/ai-content-studio.backup_"*
    rm -rf "${HOME}/.agents/skills/ai-content-studio.legacy_"*
}

#────────────────────────────────────────────────────────────────────────────
# 测试用例
#────────────────────────────────────────────────────────────────────────────

test_help_output() {
    section "测试 1: --help 参数"

    local output
    output="$("$INSTALL_SCRIPT" --help 2>&1)"

    ((TESTS_RUN++)) || true

    if echo "$output" | grep -q "Claude Code"; then
        pass "--help 输出包含 Claude Code 说明"
    else
        fail "--help 输出缺少 Claude Code 说明"
    fi

    if echo "$output" | grep -q "OpenCode"; then
        pass "--help 输出包含 OpenCode 说明"
    else
        fail "--help 输出缺少 OpenCode 说明"
    fi

    if echo "$output" | grep -q "OpenClaw"; then
        pass "--help 输出包含 OpenClaw 说明"
    else
        fail "--help 输出缺少 OpenClaw 说明"
    fi

    if echo "$output" | grep -q "\--agent"; then
        pass "--help 输出包含 --agent 参数说明"
    else
        fail "--help 输出缺少 --agent 参数说明"
    fi
}

test_syntax() {
    section "测试 2: 脚本语法检查"

    ((TESTS_RUN++)) || true

    if bash -n "$INSTALL_SCRIPT" 2>/dev/null; then
        pass "install.sh 语法正确"
    else
        fail "install.sh 语法错误"
    fi
}

test_selective_install_claude() {
    section "测试 3: --agent claude-code 选择性安装"

    # 清理
    cleanup_all

    ((TESTS_RUN++)) || true

    # 运行安装
    if "$INSTALL_SCRIPT" --agent claude-code >/dev/null 2>&1; then
        pass "--agent claude-code 执行成功"
    else
        fail "--agent claude-code 执行失败"
        return
    fi

    # 检查 Claude 链接存在
    if [[ -L "${HOME}/.claude/skills/ai-content-studio" ]]; then
        pass "Claude Code 符号链接已创建"
    else
        fail "Claude Code 符号链接未创建"
    fi

    # 检查主路径存在
    if [[ -d "${HOME}/.agents/skills/ai-content-studio" ]]; then
        pass "主安装目录已创建"
    else
        fail "主安装目录未创建"
    fi

    # 检查其他 Agent 链接不应存在
    ((TESTS_RUN++)) || true
    if [[ ! -L "${HOME}/.config/opencode/skills/ai-content-studio" ]] && \
       [[ ! -d "${HOME}/.config/opencode/skills/ai-content-studio" ]]; then
        pass "OpenCode 链接未被创建（选择性安装正确）"
    else
        fail "OpenCode 链接被错误创建"
    fi

    ((TESTS_RUN++)) || true
    if [[ ! -L "${HOME}/.openclaw/skills/ai-content-studio" ]] && \
       [[ ! -d "${HOME}/.openclaw/skills/ai-content-studio" ]]; then
        pass "OpenClaw 链接未被创建（选择性安装正确）"
    else
        fail "OpenClaw 链接被错误创建"
    fi
}

test_uninstall() {
    section "测试 4: --uninstall 完全卸载"

    # 确保有安装可卸载
    if [[ ! -d "${HOME}/.agents/skills/ai-content-studio" ]]; then
        info "需要先安装..."
        "$INSTALL_SCRIPT" --agent all >/dev/null 2>&1 || true
    fi

    ((TESTS_RUN++)) || true

    # 运行卸载
    if "$INSTALL_SCRIPT" --uninstall >/dev/null 2>&1; then
        pass "--uninstall 执行成功"
    else
        fail "--uninstall 执行失败"
        return
    fi

    # 检查所有路径已清理
    ((TESTS_RUN++)) || true
    if [[ ! -d "${HOME}/.agents/skills/ai-content-studio" ]] && \
       [[ ! -L "${HOME}/.agents/skills/ai-content-studio" ]]; then
        pass "主安装已卸载"
    else
        fail "主安装未卸载"
    fi

    ((TESTS_RUN++)) || true
    if [[ ! -L "${HOME}/.claude/skills/ai-content-studio" ]]; then
        pass "Claude Code 链接已删除"
    else
        fail "Claude Code 链接未删除"
    fi
}

test_idempotent_install() {
    section "测试 5: 幂等性测试（重复安装）"

    # 确保已安装
    if [[ ! -d "${HOME}/.agents/skills/ai-content-studio" ]]; then
        info "需要先安装..."
        "$INSTALL_SCRIPT" --agent all >/dev/null 2>&1
    fi

    ((TESTS_RUN++)) || true

    # 第二次安装（幂等测试）
    if "$INSTALL_SCRIPT" --agent all >/dev/null 2>&1; then
        pass "重复安装执行成功（幂等）"
    else
        fail "重复安装执行失败"
        return
    fi

    # 检查备份是否创建
    ((TESTS_RUN++)) || true
    if ls "${HOME}/.agents/skills/ai-content-studio.backup_"* 1>/dev/null 2>&1; then
        pass "重复安装时自动创建备份"
    else
        fail "重复安装时未创建备份"
    fi

    # 检查仍然正常工作
    ((TESTS_RUN++)) || true
    if [[ -L "${HOME}/.claude/skills/ai-content-studio" ]] && \
       [[ -d "${HOME}/.agents/skills/ai-content-studio" ]]; then
        pass "重复安装后链接仍然正常"
    else
        fail "重复安装后链接异常"
    fi
}

test_full_install() {
    section "测试 6: 全量安装（--agent all）"

    # 清理
    cleanup_all

    ((TESTS_RUN++)) || true

    # 全量安装
    if "$INSTALL_SCRIPT" --agent all >/dev/null 2>&1; then
        pass "--agent all 执行成功"
    else
        fail "--agent all 执行失败"
        return
    fi

    # 检查 4 个路径
    declare -a paths=(
        "${HOME}/.agents/skills/ai-content-studio"
        "${HOME}/.claude/skills/ai-content-studio"
        "${HOME}/.config/opencode/skills/ai-content-studio"
        "${HOME}/.openclaw/skills/ai-content-studio"
    )
    declare -a names=(
        "主路径"
        "Claude Code"
        "OpenCode"
        "OpenClaw"
    )

    for i in "${!paths[@]}"; do
        ((TESTS_RUN++)) || true
        if [[ -L "${paths[$i]}" ]] || [[ -d "${paths[$i]}" ]]; then
            pass "${names[$i]} 已创建"
        else
            fail "${names[$i]} 未创建"
        fi
    done

    # 检查主路径包含 SKILL.md
    ((TESTS_RUN++)) || true
    if [[ -f "${HOME}/.agents/skills/ai-content-studio/SKILL.md" ]]; then
        pass "SKILL.md 已复制到主路径"
    else
        fail "SKILL.md 未复制到主路径"
    fi
}

test_invalid_agent() {
    section "测试 7: 无效 --agent 参数处理"

    ((TESTS_RUN++)) || true

    # 应该返回错误
    local output
    output="$(bash "$INSTALL_SCRIPT" --agent invalid-agent 2>&1)" || true
    if echo "$output" | grep -q "错误"; then
        pass "无效 --agent 参数正确报错"
    else
        fail "无效 --agent 参数未报错（输出：$output）"
    fi
}

#────────────────────────────────────────────────────────────────────────────
# 主入口
#────────────────────────────────────────────────────────────────────────────
main() {
    echo "═══════════════════════════════════════════════"
    echo " ai-content-studio 安装脚本集成测试"
    echo "═══════════════════════════════════════════════"
    echo "  安装脚本: $INSTALL_SCRIPT"
    echo "  测试目录: $REPO_ROOT"
    echo ""

    # 前置清理
    cleanup_all

    # 运行测试
    test_help_output
    test_syntax
    test_selective_install_claude
    test_uninstall
    test_idempotent_install
    test_full_install
    test_invalid_agent

    # 最终清理
    cleanup_all

    # 输出总结
    section "测试总结"
    echo "  运行: $TESTS_RUN"
    echo -e "  通过: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  失败: ${RED}$TESTS_FAILED${NC}"
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ 所有测试通过！${NC}"
        exit 0
    else
        echo -e "${RED}✗ 有测试失败${NC}"
        exit 1
    fi
}

main "$@"
