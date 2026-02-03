#!/usr/bin/env python3
"""
allops_smart_v3.py - 二模型协作的智能决策编排器（简化加速版）
架构：Qwen3-Max（看图 + 理解 + 决策） + GUI-plus（点击定位）

特性：
- 只调用一个大脑模型（qwen3-max），减少一次往返，整体更快
- Qwen3-Max 直接看截图 + 结合任务目标和历史步骤做决策
- GUI-plus 只负责把 target_description 精确变成坐标，然后用 cliclick 执行
- 保留中文输入支持（剪贴板 + Cmd+V）
"""

import os
import sys
import time
import json
import base64
import subprocess
from openai import OpenAI

# DashScope 兼容模式 API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-xxxxxxxxxx")


# Qwen3-Max 提示词（负责看图 + 理解 + 决策）
QWEN3_MAX_PROMPT = """你是一个全模态的高级 GUI 任务助手（Qwen3-Max）。

你会同时收到：
1. 当前浏览器屏幕截图（image）
2. 用户的整体任务目标（goal）
3. 历史执行步骤（history）

你的职责：
- 直接基于截图 + 目标 + 历史，决定下一步要做什么 GUI 操作
- 输出的动作会被直接执行，所以必须谨慎、稳定
- 点击类/输入类操作会交给 GUI-plus 根据 target_description 做精确坐标定位

你的输出必须是一个 JSON 对象，格式如下：
{
  "thought": "你如何理解当前页面与任务目标，并做出决策的思考过程",
  "action": "CLICK" | "TYPE" | "SCROLL" | "KEY_PRESS" | "FINISH" | "FAIL",
  "target_description": "当 action 是 CLICK 或 TYPE 且需要依赖画面元素时，精确描述要操作的元素",
  "parameters": {
    // 根据 action 类型填充，字段含义与下面说明一致
  }
}

动作语义与参数规范：

1）CLICK（点击）
- 含义：点击某个可见元素（按钮、链接、标签页、输入框等）
- 要求：
  - target_description 必须是可在截图中定位的完整可见文本或清晰描述
  - 禁止模糊说法，例如“那个按钮”、“左边的东西”
- 示例：
{
  "action": "CLICK",
  "target_description": "页面中央搜索框右侧写着'百度一下'的蓝色按钮",
  "parameters": {}
}

2）TYPE（输入）
- 含义：在某个输入框中输入文本
- 规则：
  - 如果需要先点击输入框，请设置 parameters.click_first = true，并在 target_description 中描述该输入框
  - 中文会通过剪贴板+粘贴方式输入，你只需要给出 text 即可
- 示例：
{
  "action": "TYPE",
  "target_description": "页面中央的搜索框",
  "parameters": {
    "text": "天气预报",
    "needs_enter": false,
    "click_first": true
  }
}

3）SCROLL（滚动）
{
  "action": "SCROLL",
  "parameters": {
    "direction": "up" | "down",
    "amount": "small" | "medium" | "large"
  }
}

4）KEY_PRESS（按键）
{
  "action": "KEY_PRESS",
  "parameters": {
    "key": "enter" | "esc" | "tab" 等
  }
}

5）FINISH（任务完成）
{
  "action": "FINISH",
  "parameters": {
    "message": "任务完成的说明"
  }
}

6）FAIL（任务无法完成）
{
  "action": "FAIL",
  "parameters": {
    "reason": "清晰说明为什么无法继续"
  }
}

严格要求：
1. 只输出 JSON，不要有任何额外文字
2. action / parameters 结构必须合法、可被直接执行
3. target_description 必须足够具体，便于后续 GUI-plus 精确定位
"""


# GUI-plus 提示词（负责精确定位）
GUI_PLUS_PROMPT = """你是一个精确的坐标定位器。
用户会告诉你要点击的目标元素描述，你需要在截图中找到它并返回精确坐标。

你必须返回严格的 JSON 格式：
{
  "thought": "我在截图中看到了...",
  "found": true/false,
  "x": 坐标x,
  "y": 坐标y
}

如果找不到目标，返回：
{
  "thought": "我在截图中没有找到...",
  "found": false
}

重要：
1. 只输出 JSON
2. 坐标必须精确
3. 如果不确定，found 返回 false
"""


def take_screenshot(output: str = "/tmp/allops_smart_v3.png") -> str | None:
    """截取屏幕（强制浏览器在前台）"""
    # 方法1: 激活 Chrome
    subprocess.run(
        ["osascript", "-e", 'tell application "Google Chrome" to activate'],
        capture_output=True,
        check=False,
    )

    # 方法2: 强制设置为最前面的进程
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to set frontmost of process "Google Chrome" to true',
        ],
        check=False,
    )

    # 方法3: 确保窗口可见
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "Google Chrome" to set index of window 1 to 1',
        ],
        check=False,
    )

    # 等待窗口切换完成（v3 略快一点）
    time.sleep(0.7)

    # 截图
    subprocess.run(["screencapture", "-x", output], check=False)
    return output if os.path.exists(output) else None


def image_to_base64_url(image_path: str) -> str:
    """图片转 base64 data URL"""
    with open(image_path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")


def ask_qwen3_brain(screenshot_path: str, goal: str, history: str) -> dict | None:
    """使用 Qwen3-Max 看图 + 理解 + 决策（单模型大脑）"""
    print("\n" + "=" * 60)
    print("🧠 Qwen3-Max 分析屏幕并规划下一步...")
    print("=" * 60)

    context = {
        "goal": goal,
        "history": history or "（还没有执行任何步骤）",
        "note": "你可以直接基于截图和这些信息做下一步决策，不需要其他模型。",
    }

    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    image_url = image_to_base64_url(screenshot_path)

    try:
        completion = client.chat.completions.create(
            model="qwen3-max",
            messages=[
                {"role": "system", "content": QWEN3_MAX_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": json.dumps(context, ensure_ascii=False)},
                    ],
                },
            ],
        )

        result_text = completion.choices[0].message.content

        # 解析 JSON（兼容 ```json 包裹的情况）
        if "```json" in result_text:
            result_text = result_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```", 1)[1].split("```", 1)[0].strip()

        result = json.loads(result_text)

        print(f"\n💭 Qwen3-Max 思考: {result.get('thought', '')}")
        print(f"🎬 决定动作: {result.get('action')}")
        if result.get("action") in ["CLICK", "TYPE"]:
            print(f"🎯 目标描述: {result.get('target_description', '')}")

        return result

    except Exception as e:  # noqa: BLE001
        print(f"❌ Qwen3-Max 调用失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def ask_gui_plus(screenshot_path: str, target_description: str) -> dict:
    """使用 GUI-plus 精确定位坐标"""
    print("\n" + "=" * 60)
    print("🎯 GUI-plus 定位坐标...")
    print("=" * 60)
    print(f"目标: {target_description}")

    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    image_url = image_to_base64_url(screenshot_path)

    try:
        completion = client.chat.completions.create(
            model="gui-plus",
            messages=[
                {"role": "system", "content": GUI_PLUS_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {
                            "type": "text",
                            "text": f"请在截图中找到：{target_description}\n返回它的坐标。",
                        },
                    ],
                },
            ],
            extra_body={"vl_high_resolution_images": True},
        )

        result_text = completion.choices[0].message.content

        # 解析 JSON
        if "```json" in result_text:
            result_text = result_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```", 1)[1].split("```", 1)[0].strip()

        result = json.loads(result_text)

        print(f"\n💭 GUI-plus: {result.get('thought', '')}")

        if result.get("found"):
            x = result.get("x")
            y = result.get("y")

            # 兼容数组和单值格式
            if isinstance(x, list):
                x = int(x[0]) if x else 0
            else:
                x = int(x) if x is not None else 0

            if isinstance(y, list):
                y = int(y[0]) if y else 0
            else:
                y = int(y) if y is not None else 0

            print(f"✅ 找到了！坐标: ({x}, {y})")
            return {"found": True, "x": x, "y": y}

        print("❌ 未找到目标")
        return {"found": False}

    except Exception as e:  # noqa: BLE001
        print(f"❌ GUI-plus 定位失败: {e}")
        import traceback

        traceback.print_exc()
        return {"found": False}


def execute_action(action_result: dict | None, screenshot_path: str) -> tuple[bool, str]:
    """执行 Qwen3-Max 给出的动作"""
    if not action_result:
        return False, "决策失败"

    action = action_result.get("action")
    params = action_result.get("parameters", {}) or {}

    print("\n" + "=" * 60)
    print("▶️  执行操作")
    print("=" * 60 + "\n")

    if action == "CLICK":
        target_desc = action_result.get("target_description", "")

        # 使用 GUI-plus 获取精确坐标
        location = ask_gui_plus(screenshot_path, target_desc)
        if not location.get("found"):
            print("⚠️  无法定位目标元素")
            return False, f"无法找到：{target_desc}"

        x, y = location["x"], location["y"]

        print(f"\n🖱️  点击: {target_desc}")
        print(f"📍 坐标: ({x}, {y})")

        subprocess.run(["cliclick", f"m:{x},{y}"], check=False)
        time.sleep(0.3)
        subprocess.run(["cliclick", f"c:{x},{y}"], check=False)

        print("✅ 已点击")
        return True, f"点击了 {target_desc} ({x}, {y})"

    if action == "TYPE":
        text = params.get("text", "")
        needs_enter = params.get("needs_enter", False)
        click_first = params.get("click_first", False)
        target_desc = action_result.get("target_description", "")

        print(f"⌨️  输入: {text}")

        # 如果需要先点击输入框
        if click_first and target_desc:
            print(f"   先点击目标: {target_desc}")
            location = ask_gui_plus(screenshot_path, target_desc)
            if location.get("found"):
                x, y = location["x"], location["y"]
                print(f"   📍 输入框坐标: ({x}, {y})")
                subprocess.run(["cliclick", f"c:{x},{y}"], check=False)
                time.sleep(0.2)
            else:
                print("   ⚠️  未找到输入框，尝试直接输入")

        # 检测是否包含中文
        has_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in text)

        if has_chinese:
            print("   检测到中文，使用剪贴板方式输入...")
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=False)
            time.sleep(0.15)
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to keystroke "v" using command down',
                ],
                check=False,
            )
            print("   ✅ 已通过剪贴板粘贴")
        else:
            subprocess.run(["cliclick", f"t:{text}"], check=False)

        if needs_enter:
            subprocess.run(["cliclick", "kp:return"], check=False)

        print("✅ 已输入")
        return True, f"输入了 {text}"

    if action == "SCROLL":
        direction = params.get("direction")
        amount = params.get("amount")

        scroll_map = {"small": 3, "medium": 10, "large": 20}
        clicks = scroll_map.get(amount, 10)
        scroll_value = -clicks if direction == "up" else clicks

        print(f"🔄 滚动: {direction} ({amount})")
        subprocess.run(["cliclick", f"w:{scroll_value}"], check=False)

        print("✅ 已滚动")
        return True, f"向{direction}滚动了{amount}"

    if action == "KEY_PRESS":
        key = params.get("key", "")

        print(f"⌨️  按键: {key}")
        if "+" in key:
            subprocess.run(["cliclick", f"kp:{key}"], check=False)
        else:
            subprocess.run(["cliclick", f"kp:{key}"], check=False)

        print("✅ 已按键")
        return True, f"按下了 {key}"

    if action == "FINISH":
        message = params.get("message", "任务完成")
        print(f"✅ {message}")
        return True, message

    if action == "FAIL":
        reason = params.get("reason", "任务失败")
        print(f"❌ {reason}")
        return False, reason

    print(f"⚠️  未知动作: {action}")
    return False, f"未知动作: {action}"


def smart_execute(goal: str, max_steps: int = 20) -> None:
    """智能执行（二模型协作：Qwen3-Max + GUI-plus）"""
    print("=" * 60)
    print("🧠 allops_smart_v3 - 二模型协作版（Qwen3-Max + GUI-plus）")
    print("=" * 60)
    print(f"\n🎯 任务目标: {goal}")
    print(f"⚙️  最大步骤: {max_steps}")
    print("\n💡 架构: Qwen3-Max（看图+理解+决策） + GUI-plus（点击定位）")
    print("=" * 60)

    # 激活浏览器
    print("\n🌐 准备工作环境...")
    subprocess.run(
        ["osascript", "-e", 'tell application "Google Chrome" to activate'],
        check=False,
    )
    time.sleep(1)
    print("✅ 环境准备完成！\n")

    history: list[str] = []
    step_num = 1

    while step_num <= max_steps:
        print("\n\n" + "#" * 60)
        print(f"# 第 {step_num} 轮")
        print("#" * 60)

        # 1. 截图
        print("\n📸 截取当前屏幕...")
        screenshot = take_screenshot()
        if not screenshot:
            print("❌ 截图失败")
            break
        print("✅ 截图成功")

        # 2. Qwen3-Max 直接看图 + 做决策
        history_text = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(history))
        decision = ask_qwen3_brain(screenshot, goal, history_text)
        if not decision:
            print("\n❌ Qwen3-Max 决策失败，终止")
            break

        action = decision.get("action")

        # 3. 判断是否结束
        if action == "FINISH":
            print("\n" + "=" * 60)
            print("🎉 任务成功完成！")
            print("=" * 60)
            break

        if action == "FAIL":
            print("\n" + "=" * 60)
            print("😔 任务失败")
            print("=" * 60)
            break

        # 4. 执行动作
        success, description = execute_action(decision, screenshot)

        # 5. 记录历史（不管成功失败都记一笔，方便下一轮判断）
        history.append(description)

        # 6. 等待页面反应（比 v2 更快）
        if action in ["CLICK", "TYPE", "KEY_PRESS"]:
            print("\n⏳ 等待页面响应 (1.5秒)...")
            time.sleep(1.5)
        elif action == "SCROLL":
            print("\n⏳ 等待滚动完成 (1秒)...")
            time.sleep(1)

        step_num += 1

    if step_num > max_steps:
        print("\n" + "=" * 60)
        print(f"⚠️  达到最大步骤数 ({max_steps})，终止")
        print("=" * 60)

    # 总结
    print("\n" + "=" * 60)
    print("📊 执行总结")
    print("=" * 60)
    print(f"总步骤数: {len(history)}")
    print("\n执行历史:")
    for i, h in enumerate(history, 1):
        print(f"  {i}. {h}")
    print("=" * 60)


def main() -> None:
    if len(sys.argv) < 2:
        print("=" * 60)
        print("🧠 allops_smart_v3 - 二模型协作版（Qwen3-Max + GUI-plus）")
        print("=" * 60)
        print("\n使用方法: python3 allops_smart_v3.py '任务目标'")
        print("\n示例：")
        print("  python3 allops_smart_v3.py '打开百度搜索天气预报'")
        print("\n特点：")
        print("  ✅ Qwen3-Max 直接看图 + 理解 + 决策")
        print("  ✅ GUI-plus 负责点击与坐标定位")
        print("  ✅ 少一次模型调用，相比 v2 更快")
        print("=" * 60)
        sys.exit(1)

    goal = sys.argv[1]
    max_steps = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    smart_execute(goal, max_steps)


if __name__ == "__main__":
    main()
