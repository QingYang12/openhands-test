"""简单示例：自定义一个输出文字的工具。"""
import os
from pydantic import SecretStr
from openhands.sdk import (
    LLM,
    Action,
    Agent,
    Conversation,
    Event,
    LLMConvertibleEvent,
    Observation,
    TextContent,
    ToolDefinition,
)
from openhands.sdk.tool import ToolExecutor, register_tool, Tool

# 配置 LLM
api_key = os.getenv("LLM_API_KEY", "sk-5a839dbb64074a62a1a78e9cb6502bef")
assert api_key is not None, "LLM_API_KEY 环境变量未设置。"
model = os.getenv("LLM_MODEL", "openai/qwen3-coder-plus")
base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
llm = LLM(
    usage_id="agent",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)
# 1. 定义 Action - 工具的输入参数
class SayHelloAction(Action):
    name: str  # 要打招呼的名字


# 2. 定义 Observation - 工具的输出结果
class SayHelloObservation(Observation):
    """打招呼工具的输出"""
    pass


# 3. 定义 Executor - 工具的执行逻辑
class SayHelloExecutor(ToolExecutor):
    def __call__(self, action, conversation=None):
        # 简单地生成一段问候文字
        greeting = f"你好，{action.name}！欢迎使用自定义工具示例。今天是个美好的一天！"
        # 返回观察结果，content 需要是 TextContent 对象的列表
        return SayHelloObservation(content=[TextContent(text=greeting)])


# 4. 定义 Tool - 将以上组件组合在一起
class SayHelloTool(ToolDefinition[SayHelloAction, SayHelloObservation]):
    """一个简单的打招呼工具"""
    
    @classmethod
    def create(cls, conv_state, **params):
        return [
            cls(
                action_type=SayHelloAction,
                observation_type=SayHelloObservation,
                executor=SayHelloExecutor(),
                description="向指定的人打招呼，参数：name - 要打招呼的名字"
            )
        ]


# 5. 注册工具
register_tool("SayHello", SayHelloTool.create)

# 6. 创建带有自定义工具的 Agent
agent = Agent(llm=llm, tools=[Tool(name="SayHello")])

llm_messages = []  # 收集原始 LLM 消息


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

# 创建对话
conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback]
)

# 发送消息，让 Agent 使用我们的自定义工具
conversation.send_message("请使用 SayHello 工具向'小明'和'小红'打招呼。")
conversation.run()

print("=" * 100)
print("对话完成！")
print(f"收集到 {len(llm_messages)} 条 LLM 消息")

# 报告成本
cost = llm.metrics.accumulated_cost
print(f"\n示例成本: ${cost:.4f}" if cost > 0 else "\n示例成本: 无法计算")
print("\n提示：SayHello 工具只是简单地输出文字，不涉及任何复杂操作。")