#!/usr/bin/env python3
"""
使用阿里云 GUI-plus 模型进行屏幕操作
基于屏幕截图和自然语言指令，GUI-plus 可以解析用户意图并转换为 GUI 操作

模拟
搜索俄乌冲突 并点击  标题包含'拉夫罗夫'的新闻
"""
import os
import sys
import time
import json
import base64
import subprocess
from openai import OpenAI

# 配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-xxxxxxxxxxxxxxxxxxxxxxx")

# GUI-plus 的系统提示词（来自官方文档）
SYSTEM_PROMPT = """## 1. 核心角色 (Core Role)
你是一个顶级的AI视觉操作代理。你的任务是分析电脑屏幕截图，理解用户的指令，然后将任务分解为单一、精确的GUI原子操作。

## 2. [CRITICAL] JSON Schema & 绝对规则
你的输出**必须**是一个严格符合以下规则的JSON对象。**任何偏差都将导致失败**。
- **[R1] 严格的JSON**: 你的回复**必须**是且**只能是**一个JSON对象。禁止在JSON代码块前后添加任何文本、注释或解释。
- **[R2] 严格的Parameters结构**: thought对象的结构: "在这里用一句话简要描述你的思考过程。"
- **[R3] 精确的Action值**: action字段的值**必须**是工具集中定义的一个大写字符串（例如 "CLICK", "TYPE"），不允许有任何前导/后置空格或大小写变化。
- **[R4] 严格的Parameters结构**: parameters对象的结构**必须**与所选Action定义的模板**完全一致**。

## 3. 工具集 (Available Actions)
### CLICK
- **功能**: 单击屏幕。
- **Parameters模板**:
{
  "x": <integer>,
  "y": <integer>,
  "description": "<string, optional: 描述你点击的是什么>"
}

### TYPE
- **功能**: 输入文本。
- **Parameters模板**:
{
  "text": "<string>",
  "needs_enter": <boolean>
}

### SCROLL
- **功能**: 滚动窗口。
- **Parameters模板**:
{
  "direction": "<'up' or 'down'>",
  "amount": "<'small', 'medium', or 'large'>"
}

### KEY_PRESS
- **功能**: 按下功能键。
- **Parameters模板**:
{
  "key": "<string: e.g., 'enter', 'esc', 'alt+f4'>"
}

### FINISH
- **功能**: 任务成功完成。
- **Parameters模板**:
{
  "message": "<string: 总结任务完成情况>"
}

### FAIL
- **功能**: 任务无法完成。
- **Parameters模板**:
{
  "reason": "<string: 清晰解释失败原因>"
}

## 4. 思维与决策框架
- 目标分析: 用户的最终目标是什么？
- 屏幕观察: 仔细分析截图。你的决策必须基于截图中存在的视觉证据。
- 行动决策: 基于目标和可见的元素，选择最合适的工具。
- 构建输出: 在thought字段中记录你的思考，选择一个action，精确填充parameters。
"""


def take_screenshot(output="/tmp/guiplus_screen.png"):
    """截取屏幕"""
    print(f"📸 截图...")
    subprocess.run(["screencapture", "-x", output])
    if os.path.exists(output):
        print(f"✅ 截图成功: {output}")
        return output
    return None


def image_to_base64_url(image_path):
    """将图片转换为 base64 URL"""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    return f"data:image/png;base64,{image_data}"


def call_gui_plus(screenshot_path, user_instruction):
    """调用 GUI-plus 模型"""
    print(f"🤖 调用 GUI-plus 模型...")
    print(f"   指令: {user_instruction}")
    
    # 准备图片
    image_url = image_to_base64_url(screenshot_path)
    
    # 构建消息
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": user_instruction}
            ]
        }
    ]
    
    # 调用 OpenAI 兼容 API
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    try:
        completion = client.chat.completions.create(
            model="gui-plus",
            messages=messages,
            extra_body={"vl_high_resolution_images": True}
        )
        
        result_text = completion.choices[0].message.content
        print(f"\n📝 GUI-plus 返回:")
        print(result_text)
        print()
        
        # 解析 JSON
        # 移除可能的代码块标记
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        return result
        
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return None


def execute_action(action_result):
    """执行 GUI-plus 返回的动作"""
    if not action_result:
        return False
    
    action = action_result.get("action")
    params = action_result.get("parameters", {})
    thought = action_result.get("thought", "")
    
    print(f"💭 思考: {thought}")
    print(f"🎬 动作: {action}")
    print(f"📋 参数: {json.dumps(params, ensure_ascii=False)}")
    print()
    
    if action == "CLICK":
        x_raw, y_raw = params.get("x"), params.get("y")
        
        # 处理坐标：可能是数字或数组
        if isinstance(x_raw, list):
            x = int(x_raw[0]) if len(x_raw) > 0 else 0
        else:
            x = int(x_raw)
        
        if isinstance(y_raw, list):
            y = int(y_raw[0]) if len(y_raw) > 0 else 0
        else:
            y = int(y_raw)
        
        desc = params.get("description", "")
        print(f"🖱️  点击位置: ({x}, {y})")
        if desc:
            print(f"   描述: {desc}")
        
        # 移动鼠标
        print("1️⃣ 移动鼠标...")
        subprocess.run(["cliclick", f"m:{x},{y}"])
        
        # 等待确认
        print("⏳ 等待 3 秒...")
        time.sleep(3)
        
        # 点击
        print("2️⃣ 点击!")
        subprocess.run(["cliclick", f"c:{x},{y}"])
        print(f"✅ 已点击 ({x}, {y})")
        return True
    
    elif action == "TYPE":
        text = params.get("text", "")
        needs_enter = params.get("needs_enter", False)
        print(f"⌨️  输入文本: {text}")
        # 这里可以实现文本输入
        subprocess.run(["cliclick", f"t:{text}"])
        if needs_enter:
            subprocess.run(["cliclick", "kp:return"])
        print("✅ 已输入")
        return True
    
    elif action == "SCROLL":
        direction = params.get("direction")  # 'up' 或 'down'
        amount = params.get("amount")        # 'small', 'medium', 'large'
        
        # 转换滚动量（cliclick 的滚轮单位）
        scroll_map = {
            'small': 3,
            'medium': 10,
            'large': 20
        }
        clicks = scroll_map.get(amount, 10)
        
        # cliclick 滚动：正数向下，负数向上
        scroll_value = -clicks if direction == 'up' else clicks
        
        print(f"🔄 滚动: {direction} ({amount}) = {clicks} 单位")
        
        # 使用 cliclick 的滚轮命令 (w:N)
        subprocess.run(["cliclick", f"w:{scroll_value}"])
        
        print(f"✅ 已滚动 {direction}")
        return True
    
    elif action == "FINISH":
        message = params.get("message", "")
        print(f"✅ 任务完成: {message}")
        return True
    
    elif action == "FAIL":
        reason = params.get("reason", "")
        print(f"❌ 任务失败: {reason}")
        return False
    
    else:
        print(f"⚠️  未知动作: {action}")
        return False


def main():
    print("=" * 60)
    print("🚀 阿里云 GUI-plus 自动化操作")
    print("=" * 60)
    print()
    
    # 任务设置
    search_query = "俄乌冲突"
    target_task = "点击标题包含'拉夫罗夫'的新闻"
    
    # 1. 打开 Google 搜索
    print(f"🌐 打开 Google 搜索: {search_query}")
    url = f"https://www.google.com/search?q={search_query}"
    subprocess.run(["open", "-a", "Google Chrome", url])
    print("⏳ 等待页面加载 (6秒)...")
    time.sleep(6)
    
    # 2. 截图
    screenshot = take_screenshot()
    if not screenshot:
        print("❌ 截图失败")
        return
    
    # 3. 调用 GUI-plus
    instruction = f"在这个Google搜索结果页面中，{target_task}"
    result = call_gui_plus(screenshot, instruction)
    
    if not result:
        print("❌ GUI-plus 调用失败")
        return
    
    # 4. 执行动作
    print("=" * 60)
    print("🎬 执行动作")
    print("=" * 60)
    print()
    
    success = execute_action(result)
    
    print()
    print("=" * 60)
    if success:
        print("🎉 任务完成！")
    else:
        print("😔 任务失败")
    print("=" * 60)


if __name__ == "__main__":
    main()
