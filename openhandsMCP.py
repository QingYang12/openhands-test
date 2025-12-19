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
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
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

cwd = os.getcwd()
tools = [
    Tool(name=TerminalTool.name),
    Tool(name=FileEditorTool.name),
]

# 添加 MCP 工具
mcp_config = {
  "mcpServers": {
    "amap-amap-sse": {
      "url": "https://mcp.amap.com/sse?key=1ba843d2ae70d2ea5971c061c2235700"
    }
  }
}
# 代理
agent = Agent(
    llm=llm,
    tools=tools,
    mcp_config=mcp_config,
)

llm_messages = []  # 收集原始 LLM 消息


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())


# 对话
conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
    workspace=cwd,
)
conversation.set_security_analyzer(LLMSecurityAnalyzer())

logger.info("开始与高德地图 MCP 集成的对话...")
conversation.send_message(
    "请帮我查询北京天安门的经纬度信息。"
)
conversation.run()

conversation.send_message("再查询一下上海东方明珠的经纬度。")
conversation.run()

print("=" * 100)
print("对话已完成。收到以下 LLM 消息：")
for i, message in enumerate(llm_messages):
    print(f"消息 {i}: {str(message)[:200]}")

# 报告成本
cost = llm.metrics.accumulated_cost
print(f"示例成本: {cost}")