import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 允许你的 Gitee Pages 跨域访问这个接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContentRequest(BaseModel):
    text: str

# 统一封装调用 Coze 的函数
def call_coze(prompt: str):
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
        "stream": False,
        "auto_save_history": False,
        "additional_messages": [{"role": "user", "content": prompt, "content_type": "text"}]
    }
    
    try:
        response = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

# 功能 1：合同分析接口
@app.post("/api/scan-contract")
def scan_contract(req: ContentRequest):
    # 要求 Coze 输出结构化 JSON 便于前端渲染红绿灯警告
    return call_coze(f"你是一个法律专家。请审查以下条款，寻找霸王条款或陷阱。必须严格输出JSON，格式：{{\"risk_level\": \"高/中/低\", \"issue\": \"风险点\", \"suggestion\": \"修改建议\"}}。条款内容：{req.text}")

# 功能 2：法律问答接口
@app.post("/api/legal-qa")
def legal_qa(req: ContentRequest):
    return call_coze(f"你是一个专注农业电商的法律助手。请用大白话解答以下问题：{req.text}")
