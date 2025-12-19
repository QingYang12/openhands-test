import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.tool import Tool
from openhands.tools.browser_use import BrowserToolSet
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

# 工具
cwd = os.getcwd()
tools = [
    Tool(
        name=TerminalTool.name,
    ),
    Tool(name=FileEditorTool.name),
    Tool(name=BrowserToolSet.name),
]

# 如果你需要细粒度的浏览器控制，可以在构建 Agent 之前手动注册单个浏览器工具，
# 方法是创建一个 BrowserToolExecutor 并提供返回自定义 Tool 实例的工厂函数。

# 代理
agent = Agent(llm=llm, tools=tools)

llm_messages = []  # 收集原始 LLM 消息


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())


conversation = Conversation(
    agent=agent, callbacks=[conversation_callback], workspace=cwd
)

conversation.send_message(
    "请访问 https://top.baidu.com/board?platform=pc&sa=pcindex_entry 博客页面，并总结最新博客的主要内容。"
)
conversation.run()

print("=" * 100)
print("对话已完成。获得以下 LLM 消息：")
for i, message in enumerate(llm_messages):
    print(f"消息 {i}: {str(message)[:200]}")