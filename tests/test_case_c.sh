#!/bin/bash
# 测试案例 C：科技产品深度测评 - 广播级全环境模式

set -e

echo "=== 测试案例 C：科技产品深度测评 ==="
echo ""

# 检查源文件是否存在
if [ ! -f "折叠屏手机评测.txt" ]; then
    echo "错误: 找不到源文件: 折叠屏手机评测.txt`"
    echo "请先创建测试文件:"
    echo ""
    echo 'echo "最新折叠屏手机采用了革命性的柔性屏幕技术..." > 折叠屏手机评测.txt'
    exit 1
fi

# 检查背景音乐（可选）
BGM_FLAG=""
if [ -f "assets/tech_ambience.mp3" ]; then
    BGM_FLAG="--bgm assets/tech_ambience.mp3"
    echo "✓ 检测到背景音乐: assets/tech_ambience.mp3"
else
    echo "⚠ 未找到背景音乐，跳过 BGM"
fi

echo ""
echo "执行命令:"
echo "python3 studio_run.py \\"
echo "  --source \"折叠屏手机评测.txt\" \\"
echo "  --mode debate \\"
echo "  --stereo \\"
echo "  ${BGM_FLAG} \\"
echo "  --instruction \"Alex 负责从消费者角度提问，Sam 从技术专家角度回应\" \\"
echo "  -o outputs/debate_demo.mp3"
echo ""

# 执行测试
python3 studio_run.py \
    --source "折叠屏手机评测.txt" \
    --mode debate \
    --stereo \
    $BGM_FLAG \
    --instruction "Alex 负责从消费者角度提问、Sam 从技术专家角度回应" \
    -o outputs/debate_demo.mp3

# 检查输出
if [ -f "outputs/debate_demo.mp3" ]; then
    echo ""
    echo "✓ 测试成功"
    echo ""
    ls -lh outputs/debate_demo.mp3 | awk '{print "输出文件: " $9 " (" $5 ")"}"
    duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 outputs/debate_demo.mp3 2>/dev/null)
    echo "音频时长: ${duration} 秒"
else
    echo ""
    echo "✗ 测试失败"
    exit 1
fi
