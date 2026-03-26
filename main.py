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

def call_coze_stream(prompt: str):
    api_key = os.getenv("COZE_API_KEY")
    bot_id = os.getenv("COZE_BOT_ID")
    if not api_key or not bot_id:
        raise HTTPException(status_code=500, detail="API配置缺失")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "bot_id": bot_id,
        "user_id": "demo_user",
        "stream": True, 
        "auto_save_history": False,
        "additional_messages": [{"role": "user", "content": prompt, "content_type": "text"}]
    }
    
    try:
        resp = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=payload, stream=True)
        resp.raise_for_status()
        
        def event_stream():
            current_event = ""
            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    # 1. 记录当前是什么事件
                    if decoded_line.startswith('event:'):
                        current_event = decoded_line.split(':', 1)[1].strip()
                    # 2. 解析数据
                    elif decoded_line.startswith('data:'):
                        data_str = decoded_line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        # 🌟 核心修复：只拦截 "delta" (增量) 事件，绝不要 "completed" (完整版) 事件！
                        if current_event == "conversation.message.delta":
                            try:
                                data_json = json.loads(data_str)
                                if data_json.get("type") == "answer" and "content" in data_json:
                                    yield data_json["content"]
                            except:
                                pass
                                
        return StreamingResponse(event_stream(), media_type="text/plain")
        
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.post("/api/scan-contract")
def scan_contract(req: ContentRequest):
    return call_coze_stream(f"你是一个法律专家。请审查以下条款寻找霸王条款。请用大白话精简指出风险和修改建议。条款：{req.text}")

@app.post("/api/legal-qa")
def legal_qa(req: ContentRequest):
    return call_coze_stream(f"你是一个农业电商法律助手。请用大白话精简解答：{req.text}")
