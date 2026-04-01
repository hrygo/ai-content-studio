#!/bin/bash
# 测试案例 B：首席内参早报 - 深度对谈模式

set -e

echo "=== 测试案例 B：首席内参早报 ==="
echo ""

# 检查源文件是否存在
if [ ! -f "tests/2026Q1宏观经济报告.txt" ]; then
    echo "错误: 找不到源文件: tests/2026Q1宏观经济报告.txt"
    exit 1
fi

echo "✓ 源文件: tests/2026Q1宏观经济报告.txt"
echo ""

echo "执行命令:"
echo "python3 studio_run.py \\"
echo "  --source \"tests/2026Q1宏观经济报告.txt\" \\"
echo "  --mode deep_dive \\"
echo "  --stereo \\"
echo "  --instruction \"Sam 扮演资深策略师，Alex 扮演首席经济学家。要求去掉所有寒暄与废话，直击核心结论与风险指标\" \\"
echo "  -o outputs/首席内参_早报.mp3"
echo ""

# 执行测试
python3 studio_run.py \
    --source "tests/2026Q1宏观经济报告.txt" \
    --mode deep_dive \
    --stereo \
    --instruction "Sam 扮演资深策略师，Alex 扮演首席经济学家。要求去掉所有寒暄与废话，直击核心结论与风险指标" \
    -o outputs/首席内参_早报.mp3

# 检查输出
if [ -f "outputs/首席内参_早报.mp3" ]; then
    echo ""
    echo "✓ 测试成功"
    echo ""
    ls -lh outputs/首席内参_早报.mp3 | awk '{print "输出文件: " $9 " (" $5 ")"}'
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "outputs/首席内参_早报.mp3" 2>/dev/null)
    echo "音频时长: ${duration} 秒"
else
    echo ""
    echo "✗ 测试失败"
    exit 1
fi
