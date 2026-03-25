import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContentRequest(BaseModel):
    text: str

# 🌟 全新的流式调用函数
def call_coze_stream(prompt: str):
    api_key = os.getenv("COZE_API_KEY")
    bot_id = os.getenv("COZE_BOT_ID")
    if not api_key or not bot_id:
        raise HTTPException(status_code=500, detail="API配置缺失")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 开启 stream: True，且不需要再存历史记录了
    payload = {
        "bot_id": bot_id,
        "user_id": "demo_user",
        "stream": True, 
        "auto_save_history": False,
        "additional_messages": [{"role": "user", "content": prompt, "content_type": "text"}]
    }
    
    try:
        # 发起流式请求
        resp = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=payload, stream=True)
        resp.raise_for_status()
        
        # 这是一个生成器，专门从 Coze 吐出的数据里剥离出有用的汉字
        def event_stream():
            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data:'):
                        data_str = decoded_line[5:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            # 只抓取类型为 answer 的文本内容
                            if data_json.get("type") == "answer" and "content" in data_json:
                                yield data_json["content"]
                        except:
                            pass
                            
        # 返回流式响应
        return StreamingResponse(event_stream(), media_type="text/plain")
        
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.post("/api/scan-contract")
def scan_contract(req: ContentRequest):
    # 增加了一个小技巧：要求 AI 精简字数，输出越少速度越快
    return call_coze_stream(f"你是一个法律专家。请审查以下条款，寻找霸王条款或陷阱。请用100字以内的纯大白话指出风险和修改建议。条款内容：{req.text}")

@app.post("/api/legal-qa")
def legal_qa(req: ContentRequest):
    return call_coze_stream(f"你是一个专注农业电商的法律助手。请用大白话精简地（150字以内）解答以下问题：{req.text}")
