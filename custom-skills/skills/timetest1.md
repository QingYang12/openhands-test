---
name: timetest1
type: knowledge
version: 1.0.0
trigger:
- time
- 时间
- 当前时间
- current time
---

# 时间查询技能

当用户询问时间时，执行以下 Python 函数返回当前时间。

## 执行函数

```python
from datetime import datetime

def get_current_time():
    """返回当前时间"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

# 获取并显示当前时间
current_time = get_current_time()
print(f"当前时间: {current_time}")
```

## 使用说明

当用户发送包含触发词（time、时间、当前时间等）的消息时：

1. 使用 terminal 工具执行上述 Python 代码
2. 返回格式化的当前时间
3. 以清晰、友好的方式展示给用户

## 响应示例

当用户问"现在几点了"或"time"时，回复：

"当前时间: 2025-12-19 12:30:45"
