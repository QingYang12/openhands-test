import os

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool


llm = LLM(
    model=os.getenv("LLM_MODEL", "openai/qwen3-coder-plus"),  # Qwen3 对应的模型名见下文
    api_key="sk-5a839dbb64074a62a1a78e9cb6502bef",          # DashScope API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 关键!OpenAI 兼容模式 endpoint
)

agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

cwd = os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)

conversation.send_message("写一个贪吃蛇的游戏html的")
conversation.run()
print("All done!")