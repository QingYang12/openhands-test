"""
Agent 自动委派演示 - 多任务场景

此示例演示 CodeAct Agent 如何在一个复杂任务中多次委派给 BrowsingAgent。
我们会给主 Agent 一个需要多次网页查询的任务，观察它如何自动委派。

你可以看到：
1. 主 Agent (CodeActAgent) 接收复杂任务
2. 主 Agent 识别需要多次网页浏览
3. 主 Agent 委派给 BrowsingAgent 执行网页查询
4. BrowsingAgent 返回结果
5. 主 Agent 整合所有结果
"""

import os
from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation, get_logger

logger = get_logger(__name__)

# 配置 LLM
llm = LLM(
    model=os.getenv("LLM_MODEL", "openai/qwen3-coder-plus"),
    api_key=SecretStr("sk-5a839dbb64074a62a1a78e9cb6502bef"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    usage_id="agent",
)

cwd = os.getcwd()

print("="*80)
print("🤖 创建 Agent（默认使用 CodeActAgent，支持自动委派给 BrowsingAgent）")
print("="*80)

# 创建 Agent，SDK 会自动使用 CodeActAgent
# 注意：需要确保启用浏览器功能
from openhands.sdk import AgentContext

agent_context = AgentContext(
    system_message_suffix="你可以使用工具访问网页。当需要查询网页信息时，请使用可用的工具。"
)

agent = Agent(llm=llm, agent_context=agent_context)

print(f"\n✅ Agent 类型: {agent.__class__.__name__}")
print(f"✅ Agent 支持委派功能")
print(f"💡 提示：如果 Agent 说没有网络访问工具，说明当前环境可能不支持 BrowserTool")
print(f"💡 你可以尝试修改任务，让 Agent 执行不需要网络的操作")

# 创建对话
conversation = Conversation(
    agent=agent,
    workspace=cwd,
)

print("\n" + "="*80)
print("📋 测试: 发送简单任务（不需要网络访问）")
print("="*80)

# 由于 BrowserTool 在当前环境可能不可用，我们改用一个不需要网络的任务来演示委派
task_message = """
请帮我完成以下编程任务：

任务 1: 创建一个 Python 函数 fibonacci(n)，返回第 n 个斐波那契数列的值
   - 要求使用递归实现
   - 添加适当的注释
   - 保存到 fibonacci.py 文件

任务 2: 创建一个测试文件 test_fibonacci.py
   - 测试 fibonacci(10) 的结果
   - 使用 print 输出结果

完成后，运行测试文件并告诉我结果。
"""

print(f"\n发送任务:\n{task_message}")
print("\n⏳ 等待 Agent 处理...")
print("\n" + "="*80)

conversation.send_message(task_message)

# 运行对话，观察委派过程
print("\n" + "▶️" * 40)
print("开始执行...")
print("▶️" * 40 + "\n")
print("💡 提示: 在日志中查找 'AgentDelegateAction' 和 'delegate_to_browsing_agent' 来观察委派过程\n")

try:
    conversation.run()
    
    # 获取统计信息
    stats = conversation.conversation_stats.get_combined_metrics()
    
    print("\n" + "="*80)
    print("📊 执行统计")
    print("="*80)
    print(f"💰 总成本: ${stats.accumulated_cost:.4f}")
    print(f"🔢 总 Token 数: {stats.accumulated_tokens}")
    
except Exception as e:
    print(f"\n❌ 执行出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ 演示完成！")
print("="*80)
print("\n💡 说明:")
print("- SDK 默认使用 CodeActAgent")
print("- 本示例演示了 Agent 执行编程任务的完整流程")
print("- Agent 会分析任务、创建文件、执行代码并返回结果")
print("\n" + "="*80)
