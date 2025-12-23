---
name: web_search
type: knowledge
version: 1.0.0
trigger:
- 搜索
- 查询
- search
- 联网
- 网络搜索
---

# 联网搜索技能

当用户需要联网搜索信息时，通过 Dify API 执行搜索并返回结果。

## 执行函数

```python
import json
import subprocess

def web_search(query):
    """
    使用 Dify API 进行联网搜索
    
    参数:
        query: 用户要搜索的内容
    
    返回:
        搜索结果的 JSON 数据
    """
    # 构建 curl 命令
    cmd = [
        'curl', '-X', 'POST',
        'http://dify.wanghaonet.com/v1/workflows/run',
        '-H', 'Authorization: Bearer app-LNBwO3ZbTbiXOSZb4snSQe2M',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "inputs": {
                "query": query
            },
            "user": "wanghao_test_user_001",
            "response_mode": "blocking"
        })
    ]
    
    # 执行命令
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 返回结果
    if result.returncode == 0:
        return result.stdout
    else:
        return f"搜索失败: {result.stderr}"

# 使用示例
# query = "今天北京天气怎么样？"  # 这里替换为用户的查询内容
# result = web_search(query)
# print(result)
```

## 使用说明

当用户发送包含触发词（搜索、查询、search、联网等）的消息时：

1. 提取用户要搜索的关键词或问题
2. 使用 terminal 工具执行上述 Python 代码，将用户的查询内容传入 `query` 参数
3. 解析返回的 JSON 结果
4. 以清晰、友好的方式将搜索结果展示给用户

## 响应示例

当用户问"搜索今天北京天气怎么样"时：

1. 执行 `web_search("今天北京天气怎么样？")`
2. 获取搜索结果
3. 将结果整理后返回给用户
