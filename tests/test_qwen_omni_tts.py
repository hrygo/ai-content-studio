"""
Qwen Omni TTS 真实测试案例
测试场景：
  1. 基础合成：产品发布公告朗读
  2. 多角色对话：真实博客文章 → 播客风格对谈（立体声）
  3. 全流程 Studio：深度文章 → 摘要播报
  4. BGM 混音：生活方式类博客 → 背景音乐伴随
"""
import os
import sys
import time
import subprocess

# 路径
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from qwen_omni_tts_tool import (
    load_api_config,
    text_to_speech_qwen,
    parse_dialogue_text,
    process_segments,
)
from qwen_omni_studio import run_full

OUTPUTS = os.path.join(ROOT, "outputs")
os.makedirs(OUTPUTS, exist_ok=True)


def _ts():
    return int(time.time() * 1000)


def get_duration(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.DEVNULL,
        )
        return float(out.decode().strip())
    except Exception:
        return 0.0


def file_exists_and_nonzero(path):
    return os.path.exists(path) and os.path.getsize(path) > 1024


# ──────────────────────────────────────────────────────────────
# 博客真实内容
# ──────────────────────────────────────────────────────────────

BLOG_SCENE1 = """小米15 Ultra 正式发布：影像旗舰再进化，6499元起售
小米今晚如期发布了年度影像旗舰小米15 Ultra，搭载骁龙8至尊版处理器，首发全新1英寸LYT-900传感器，
配合徕卡双长焦镜头，实现从超广角到潜望长焦的全焦段覆盖。月亮模式升级至10倍光学变焦，
手持即可拍出专业级天文照片。起售价6499元，2月正式开售。"""

BLOG_SCENE2_ARTICLE = """
AI 代码助手现状：Copilot、Cursor 与国产新势力的真实对比

近年来，AI 代码助手从概念走向普及。本文作者实际使用三个月后，带来这份深度横评。

先说结论：没有完美工具，只有适合的场景。

GitHub Copilot 是最早大规模商用的产品，背靠 OpenAI 的模型能力，在简单补全和注释生成上表现出色。
但它的短板也很明显：对中文注释的理解有限，偶尔生成安全风险较高的 SQL 或文件操作代码。

Cursor 则走出了另一条路。它将 AI 对话深度整合进 VS Code 编辑器，Tab 补全、Agent 模式、
项目级上下文理解构成了完整工作流。尤其是 0.6 版本引入的 Compose 模式，可以跨文件理解代码意图，
在重构和大型需求改造场景中明显优于竞品。

国产阵营中，豆包代码助手依托字节跳动的模型积累，在中文场景下体验最自然，
部分垂类场景（小程序、Web 前端）的代码生成质量已经不输 Copilot。
而通义灵码在阿里系技术栈（Java、Spring、Vue）上的深度优化，是其独特优势。

综合来看，专业前端推荐 Cursor，追求性价比选 Copilot，
阿里技术栈为主则通义灵码性价比最高。"""

BLOG_SCENE2_DIALOGUE = [
    ("主持人", "neutral", "欢迎收听本期技术观察，今天我们来聊聊 AI 代码助手的现状。"),
    ("极客A", "excited",
     "好的！这个话题我太有发言权了。我用 Copilot、Cursor，还有豆包和通义灵码，大概有三个月时间。"),
    ("主持人", "neutral", "那先说说结论？"),
    ("极客A", "neutral",
     "结论就是：没有完美工具，只有适合的场景。先说 Copilot，它是商用最早的，背靠 OpenAI 模型，简单补全和注释生成确实不错。"),
    ("技术B", "skeptical",
     "但短板也很明显吧？我用的时候，它对中文注释的理解非常有限，有时候生成 SQL 或者文件操作代码，还有安全风险。"),
    ("极客A", "neutral",
     "对，这是 Copilot 最被诟病的地方。那 Cursor 呢，它走的是另一条路。Tab 补全、Agent 模式、项目级上下文理解，三件事打通了，0.6 版本的 Compose 模式尤其惊艳。"),
    ("技术B", "calm",
     "跨文件理解代码意图，重构场景确实强。但我更关心的是，Cursor 对中文开发者友好吗？"),
    ("极客A", "neutral",
     "说实话，比 Copilot 好，但豆包在中文场景下体验最自然。尤其小程序和 Web 前端，代码生成质量已经不输 Copilot 了。"),
    ("主持人", "neutral",
     "国产里面还有什么值得关注的选择吗？"),
    ("极客A", "happy",
     "通义灵码！它在阿里系技术栈——Java、Spring、Vue 上做了深度优化，这是它独特的护城河。如果你在阿里工作，通义灵码的性价比最高。"),
    ("主持人", "neutral",
     "好的，来总结一下：前端开发者推荐 Cursor，追求性价比选 Copilot，阿里技术栈选通义灵码。感谢两位的精彩讨论！"),
]

BLOG_SCENE3 = """
拒绝焦虑：为什么你需要重新定义「效率」

这是一个被效率崇拜绑架的时代。

我们每天都在被催促：早起、列清单、追踪时间、批量处理、番茄钟……
你以为自己在掌控时间，其实时间在悄悄吞噬你。

真正的效率不是塞满每一分钟，而是找到对你重要的事，然后心无旁骛地做。

具体怎么做？

第一，把「必须完成」的清单缩短到三件事。超过三件，大脑会自动将其归类为「不可能完成」而放弃。
第二，给自己留白。心理学研究表明，创造力往往在放空时达到峰值。
第三，停止多任务。切换成本比你想象的高得多，每一次分心后平均需要23分钟才能完全回到原任务。

记住：不是所有事情都值得高效完成的。
那些真正重要的事，值得你慢下来，好好做。"""

BLOG_SCENE4_ARTICLE = """
极简主义两年后：我的10个生活习惯改变

两年前，我做了人生中最重要的一次「断舍离」。

不是扔东西那么简单，而是一次思维上的彻底重构——从「拥有更多」到「需要更少」。

两年过去了，我的10个生活习惯已经彻底改变。

第一，早起不再是痛苦。以前6点起床是为了赶任务，现在是为了那一段完全属于自己的安静时光。
第二，衣柜从80件精简到15件。每天出门不再为穿什么纠结，省下的精力去做真正重要的决定。
第三，购物前必问自己一个问题：这个东西买了之后，会让我的生活更简单，还是更复杂？
第四，手机通知全部关闭，只保留来电和家人、合作伙伴的紧急短信。
第五，社交上做减法，10个深度朋友胜过1000个点赞之交。
第六，放弃了碎片化阅读，改为每天固定30分钟深度阅读，纸质书。
第七，每月一次「无消费日」，刻意体验匮乏感，减少冲动购物。
第八，简化饮食，工作日基本是固定的健康餐，节假日才允许自己放开。
第九，给生活留白。以前总要把日程排满，现在允许自己「什么都没做」而不内疚。
第十，不再追求平衡，允许自己有时工作狂、有时完全躺平，接受生活的非线性。

极简主义不是苦行僧，而是一种清醒。
知道自己是谁，知道什么重要，然后把不重要的事勇敢删掉。"""


# ──────────────────────────────────────────────────────────────
# 场景 1: 博客开篇公告 → 单人朗读
# ──────────────────────────────────────────────────────────────

def test_scene1_announcement():
    """场景1：科技产品发布公告朗读"""
    key, url = load_api_config()
    assert key, "未配置 DashScope API Key"

    # 准备博客开篇稿（真实风格）
    blog_text = (
        "欢迎来到我的科技频道。今天我们聊一个重磅新品——小米15 Ultra。 "
        "这款手机昨晚正式发布，6499元起售。 "
        "最大的亮点是影像系统，搭载了全新1英寸LYT-900传感器，配合徕卡双长焦镜头，实现了从超广角到潜望长焦的全焦段覆盖。 "
        "最让我惊喜的是月亮模式，升级到10倍光学变焦，手持就能拍出专业级的天文照片。 "
        "如果你对移动摄影有追求，这款手机值得关注。2月正式开售，我会持续跟进评测。 "
    )

    out = os.path.join(OUTPUTS, f"auto_{_ts()}_scene1_blog_announcement.mp3")

    result = text_to_speech_qwen(
        text=blog_text,
        output_file=out,
        voice="cherry",
        api_key=key,
        api_url=url,
    )

    assert result is not None, "TTS 返回为空"
    assert file_exists_and_nonzero(out), f"输出文件为空: {out}"

    duration = get_duration(out)
    assert 10.0 <= duration <= 60.0, f"音频时长异常: {duration}s"

    print(f"  ✓ 场景1 通过 | 产品公告 | {duration:.1f}s | {os.path.basename(out)}")


# ──────────────────────────────────────────────────────────────
# 场景 2: 真实博客文章 → 双人播客对谈（立体声）
# ──────────────────────────────────────────────────────────────

def test_scene2_blog_podcast():
    """场景2：AI 代码助手横评博客 → 播客风格对谈"""
    key, url = load_api_config()
    assert key, "未配置 DashScope API Key"

    roles = {
        "主持人": {"voice": "cherry",  "emotion": "neutral"},
        "极客A":  {"voice": "ethan",   "emotion": "neutral"},
        "技术B":  {"voice": "ethan",   "emotion": "calm"},
    }

    dialogue_path = os.path.join(OUTPUTS, f"auto_{_ts()}_scene2_podcast_script.txt")
    with open(dialogue_path, "w", encoding="utf-8") as f:
        for role, emotion, line in BLOG_SCENE2_DIALOGUE:
            f.write(f"[{role}, {emotion}]: {line}\n")

    out = os.path.join(OUTPUTS, f"auto_{_ts()}_scene2_blog_podcast.mp3")

    segments = parse_dialogue_text(dialogue_path)
    assert len(segments) >= 8, f"对话片段不足: {len(segments)}"

    success = process_segments(
        segments,
        output_file=out,
        roles=roles,
        use_stereo=True,
        api_key=key,
        api_url=url,
    )

    assert success, "多角色播客合成失败"
    assert file_exists_and_nonzero(out), f"输出文件为空: {out}"

    duration = get_duration(out)
    assert duration >= 3.0, f"播客时长过短: {duration}s"

    # 验证立体声
    stereo = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=channels",
         "-of", "csv=p=0", out],
        capture_output=True, text=True,
    )
    assert "2" in stereo.stdout, f"非立体声: {stereo.stdout}"

    print(f"  ✓ 场景2 通过 | 播客对谈 {len(segments)}段 | {duration:.1f}s | 立体声 | {os.path.basename(out)}")


# ──────────────────────────────────────────────────────────────
# 场景 3: 深度博客文章 → 全流程摘要播报
# ──────────────────────────────────────────────────────────────

def test_scene3_blog_summary():
    """场景3：深度博客 → Studio 全流程摘要"""
    key, url = load_api_config()
    assert key, "未配置 DashScope API Key"

    # 先写文件（避免长字符串触发 Path.exists() OSError）
    src_file = os.path.join(OUTPUTS, f"auto_{_ts()}_scene3_source.txt")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write(BLOG_SCENE3)

    out = os.path.join(OUTPUTS, f"auto_{_ts()}_scene3_blog_summary.mp3")

    ok = run_full(
        source=src_file,
        mode="summary",
        output_file=out,
        instruction="专业播音，语速适中，内容忠实原文，不要翻译或改写",
        voice="ethan",
        verbose=True,
    )

    assert ok, "全流程摘要失败"
    assert file_exists_and_nonzero(out), f"输出文件为空: {out}"

    duration = get_duration(out)
    assert duration >= 10.0, f"摘要时长过短: {duration}s"

    print(f"  ✓ 场景3 通过 | 博客摘要 | {duration:.1f}s | {os.path.basename(out)}")


# ──────────────────────────────────────────────────────────────
# 场景 4: 生活方式博客 → 背景音乐混音
# ──────────────────────────────────────────────────────────────

def test_scene4_blog_with_bgm():
    """场景4：生活方式博客 → 背景音乐伴随朗读"""
    key, url = load_api_config()
    assert key, "未配置 DashScope API Key"

    roles = {
        "主播": {"voice": "cherry", "emotion": "neutral"},
    }

    # 博客完整文章 → 单人播报
    out = os.path.join(OUTPUTS, f"auto_{_ts()}_scene4_blog_with_bgm.mp3")

    # 准备 BGM：柔和的环境音（低频单音 + 低音量）
    bgm = os.path.join(OUTPUTS, f"auto_{_ts()}_ambient_bgm.mp3")
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", "sine=frequency=220:duration=30",
         "-af", "volume=0.10",
         "-codec:a", "libmp3lame", "-b:a", "64k", bgm],
        capture_output=True,
    )

    # 文章解析为对话片段（博客原文 → Narrator 播报格式）
    article_segments = [{"role": "主播", "emotion": "neutral", "text": BLOG_SCENE4_ARTICLE.strip()}]

    success = process_segments(
        article_segments,
        output_file=out,
        roles=roles,
        use_stereo=False,
        api_key=key,
        api_url=url,
        bgm_file=bgm,
    )

    assert success, "BGM 混音合成失败"
    assert file_exists_and_nonzero(out), f"输出文件为空: {out}"

    duration = get_duration(out)
    assert duration >= 20.0, f"混音时长过短: {duration}s"

    print(f"  ✓ 场景4 通过 | 博客+背景音乐 | {len(article_segments)}段 | {duration:.1f}s | {os.path.basename(out)}")


# ──────────────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Qwen Omni TTS 博客真实测试")
    parser.add_argument("scene", nargs="?", choices=["1","2","3","4","all"], default="all")
    args = parser.parse_args()

    scenes = {
        "1": ("场景1: 博客开篇公告朗读",       test_scene1_announcement),
        "2": ("场景2: AI助手横评 → 播客对谈",   test_scene2_blog_podcast),
        "3": ("场景3: 博客深度文 → 摘要播报",   test_scene3_blog_summary),
        "4": ("场景4: 生活方式博客 → BGM混音", test_scene4_blog_with_bgm),
    }

    print("=" * 55)
    print("Qwen Omni TTS 博客真实案例测试")
    print("=" * 55)

    if args.scene == "all":
        for scene_id, (name, fn) in scenes.items():
            print(f"\n>>> {name}")
            t0 = time.time()
            try:
                fn()
            except AssertionError as e:
                print(f"  ✗ 断言失败: {e}")
            except Exception as e:
                print(f"  ✗ 异常: {e}")
            print(f"  耗时: {time.time()-t0:.1f}s")
        print("\n" + "=" * 55)
        print("全部场景执行完成")
    else:
        name, fn = scenes[args.scene]
        print(f">>> {name}")
        fn()
