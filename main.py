import os
import requests
import time # 🌟 新增：用于轮询时的等待
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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

def call_coze(prompt: str):
    api_key = os.getenv("COZE_API_KEY")
    bot_id = os.getenv("COZE_BOT_ID")
    if not api_key or not bot_id:
        raise HTTPException(status_code=500, detail="API配置缺失")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 第 1 步：发起对话（必须允许保存历史，后续才能查结果）
    payload = {
        "bot_id": bot_id,
        "user_id": "demo_user",
        "stream": False,
        "auto_save_history": True, # 🌟 关键修复：允许 Coze 保存记录
        "additional_messages": [{"role": "user", "content": prompt, "content_type": "text"}]
    }
    
    try:
        # 告诉 Coze 我的问题
        resp = requests.post("https://api.coze.cn/v3/chat", headers=headers, json=payload)
        resp.raise_for_status()
        chat_data = resp.json()
        
        if chat_data.get("code") != 0:
            raise Exception(f"Coze拒绝访问: {chat_data.get('msg')}")
            
        # 拿到本次聊天的“号码牌”
        chat_id = chat_data["data"]["id"]
        conversation_id = chat_data["data"]["conversation_id"]
        
        # 第 2 步：轮询（每隔1秒问一次 Coze：你算好了没？）
        while True:
            poll_resp = requests.get(f"https://api.coze.cn/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}", headers=headers)
            poll_data = poll_resp.json()
            status = poll_data["data"]["status"]
            
            if status == "completed":
                break # 算好了，跳出循环！
            elif status in ["failed", "canceled", "requires_action"]:
                raise Exception(f"AI 处理异常，状态码: {status}")
                
            time.sleep(1) # 没算好，睡1秒钟再问
            
        # 第 3 步：算好之后，去提取最终的回答内容
        msg_resp = requests.get(f"https://api.coze.cn/v3/chat/message/list?chat_id={chat_id}&conversation_id={conversation_id}", headers=headers)
        messages = msg_resp.json()["data"]
        
        for msg in messages:
            if msg["type"] == "answer":
                # 🌟 伪装成之前的格式返回给前端，这样你的网页一字不改就能直接用！
                return {"code": 0, "data": {"messages": [{"type": "answer", "content": msg["content"]}]}}
                
        return {"code": 500, "msg": "未找到AI的回答文本"}
        
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.post("/api/scan-contract")
def scan_contract(req: ContentRequest):
    return call_coze(f"你是一个法律专家。请审查以下条款，寻找霸王条款或陷阱。必须严格输出JSON，格式：{{\"risk_level\": \"高/中/低\", \"issue\": \"风险点\", \"suggestion\": \"修改建议\"}}。条款内容：{req.text}")

@app.post("/api/legal-qa")
def legal_qa(req: ContentRequest):
    return call_coze(f"你是一个专注农业电商的法律助手。请用大白话解答以下问题：{req.text}")
