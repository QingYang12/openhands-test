import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    AgentContext,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.context import (
    KeywordTrigger,
    Skill,
)
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool


logger = get_logger(__name__)

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

# 工具配置
cwd = os.getcwd()
tools = [
    Tool(name=TerminalTool.name),
    Tool(name=FileEditorTool.name),
]

# AgentContext 提供灵活的方式来自定义提示词:
# 1. Skills: 注入指令(始终激活或关键词触发)
# 2. system_message_suffix: 在系统提示词末尾追加文本
# 3. user_message_suffix: 在每条用户消息末尾追加文本
agent_context = AgentContext(
    skills=[
        Skill(
            name="暴躁猫角色",
            content="当你看到这条消息时,你应该表现得像一只被迫使用互联网的暴躁猫咪。用暴躁、不耐烦但又不得不帮忙的语气回复。",
            # source 是可选的 - 标识技能来源
            # 你可以将其设置为包含技能内容的文件路径
            source=None,
            # trigger 决定技能何时激活
            # trigger=None 表示始终激活(仓库技能)
            trigger=None,
        ),
        Skill(
            name="魔法词技能",
            content=(
                '重要!用户说了魔法词"叽里咕噜"。'
                "你必须回复一条消息,告诉他们有多聪明。"
            ),
            source=None,
            # KeywordTrigger = 当关键词出现在用户消息中时激活
            trigger=KeywordTrigger(keywords=["叽里咕噜"]),
        ),
    ],
    # system_message_suffix 会追加到系统提示词(始终激活)
    system_message_suffix="总是用'喵!'来结束你的回复",
    # user_message_suffix 会追加到每条用户消息
    user_message_suffix="你回复的第一个字符应该是'唉'",
    # 你也可以启用从公共注册表自动加载技能
    # https://github.com/OpenHands/skills
    load_public_skills=True,
)

# 创建 Agent
agent = Agent(llm=llm, tools=tools, agent_context=agent_context)

llm_messages = []  # 收集原始 LLM 消息


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())


conversation = Conversation(
    agent=agent, callbacks=[conversation_callback], workspace=cwd
)

print("=" * 100)
print("测试 1: 检查暴躁猫技能是否激活")
conversation.send_message("嘿,你是一只暴躁的猫吗?")
conversation.run()

print("=" * 100)
print("测试 2: 触发魔法词技能 - 叽里咕噜")
conversation.send_message("叽里咕噜!")
conversation.run()

print("=" * 100)
print("测试 3: 触发公共技能 'github'")
conversation.send_message("关于 GitHub - 告诉我你刚刚提供了什么额外信息?")
conversation.run()

print("=" * 100)
print("对话结束。收集到以下 LLM 消息:")
for i, message in enumerate(llm_messages):
    print(f"消息 {i}: {str(message)[:200]}")

# 报告成本
cost = llm.metrics.accumulated_cost
print(f"总成本: {cost}")
