import mimetypes
import random
import time
from typing import Literal

import httpx
from .schemas import *


def random_delay(min_seconds=1, max_seconds=3):
    """Sleep for a random delay between min and max seconds."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def create_message(role: Literal["system", "user", "assistant"], **kwargs) -> AnyInternalMessage | None:
    """
    一个静态的、纯粹的消息创建工厂函数。
    根据 role 和关键字参数，构建相应的 InternalMessage 对象并返回。
    它不修改任何状态，只负责创建。

    用法:
    msg = ChatSession.create_message(role="user", text="你好")
    """
    role_map = {
        "system": SystemInternalMessage,
        "user": UserInternalMessage,
        "assistant": AssistantInternalMessage,
        "tool": ToolInternalMessage,
    }
    content = []

    if role == "system":
        content = [TextBlock(text=kwargs['text'])]

    elif role == "user":
        if 'text' in kwargs:
            content.append(TextBlock(text=kwargs['text']))
        if 'image_data' in kwargs and 'mime_type' in kwargs:
            content.append(ImageBlock(image_data=kwargs['image_data'], mime_type=kwargs['mime_type']))

    elif role == "assistant":
        if 'text' in kwargs:
            content.append(TextBlock(text=kwargs['text']))
        if 'tool_requests' in kwargs:
            content.extend([ToolCallRequestBlock(**tool_request) for tool_request in kwargs['tool_requests']])
    
    # 注意：ToolInternalMessage 通常由 tool_results 列表直接创建，所以这里不包含 "tool" role
    # ToolInternalMessage(content=tool_results)

    if not content:
        print(f"警告：调用 create_message 时，为 role='{role}' 提供的参数不足，无法创建消息。")
        return None

    return role_map[role](content=content)
