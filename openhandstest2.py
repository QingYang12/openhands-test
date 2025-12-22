"""OpenHands HTTP 服务 - 通过 HTTP API 调用 Agent"""
# 测试用HTTP调用
# 启动后 服务 : http://localhost:8123/
# 调用进行交谈  同步返回 : http://localhost:8123/chat
# 调用进行交谈  异步返回 : http://localhost:8123/chat-async

# 测试启动后执行如下命令:
#    curl -X POST "http://localhost:8123/chat"  -H "Content-Type: application/json"  -d '{"message": "写一个贪吃蛇的游戏html的"}'

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

app = FastAPI(title="OpenHands HTTP Service", version="1.0")


# 请求模型
class ChatRequest(BaseModel):
    message: str
    workspace: str | None = None  # 可选的工作目录


# 响应模型
class ChatResponse(BaseModel):
    status: str
    message: str
    workspace: str | None = None


# 初始化 LLM（全局共享）
llm = LLM(
    model=os.getenv("LLM_MODEL", "openai/qwen3-coder-plus"),
    api_key=os.getenv("LLM_API_KEY", "sk-5a839dbb64074a62a1a78e9cb6502bef"),
    base_url=os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)


@app.get("/")
async def root():
    """健康检查接口"""
    return {"status": "ok", "service": "OpenHands HTTP Service"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    接收用户消息并通过 Agent 处理

    参数:
        message: 用户的任务描述
        workspace: 工作目录（可选，默认使用当前目录）

    返回:
        status: 执行状态
        message: 响应消息
        workspace: 使用的工作目录
    """
    try:
        # 创建 Agent
        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
                Tool(name=TaskTrackerTool.name),
            ],
        )

        # 确定工作目录
        workspace = request.workspace or os.getcwd()

        # 创建对话
        conversation = Conversation(agent=agent, workspace=workspace)

        # 发送消息并运行
        conversation.send_message(request.message)
        conversation.run()

        return ChatResponse(
            status="success",
            message=f"任务已完成：{request.message}",
            workspace=workspace
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/chat-async", response_model=ChatResponse)
async def chat_async(request: ChatRequest):
    """
    异步版本 - 立即返回，任务在后台执行
    （简化版本，实际使用建议配合任务队列如 Celery）
    """
    try:
        # 这里可以将任务放入队列，立即返回任务 ID
        # 实际实现需要配合 Redis/RabbitMQ 等
        return ChatResponse(
            status="queued",
            message=f"任务已加入队列：{request.message}",
            workspace=request.workspace or os.getcwd()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务入队失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8123)



