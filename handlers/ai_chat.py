import requests
import base64
from config import AI_API_KEY
from database import db

def get_prime_ai_response(user_id, query):
    if not AI_API_KEY: 
        return "❌ کلیل نییە."
    try:
        # وەرگرتنی مێژووی نامەکان بۆ ئەوەی مێشکەکە بیر بکاتەوە
        history = db().execute("SELECT role, content FROM chat_history WHERE user_id=? ORDER BY id DESC LIMIT 6", (user_id,)).fetchall()
        history.reverse()
        
        contents = [{"role": role, "parts": [{"text": content}]} for role, content in history]
        contents.append({"role": "user", "parts": [{"text": query}]})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={AI_API_KEY}"
        
        system_prompt = (
            "You are BLACK HAT AI PRIME, an elite AI expert in technology, hacking, and programming. "
            "Always reply in the exact same language the user used. Be incredibly precise and detailed."
        )
        
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
        }
        
        response = requests.post(url, json=payload, timeout=40)
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            ai_text = data['candidates'][0]['content']['parts'][0]['text']
            
            # تۆمارکردنی نامەکان لە داتابەیس بۆ بیرکردنەوەی داهاتوو
            db().execute("INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)", (user_id, "user", query))
            db().execute("INSERT INTO chat_history(user_id, role, content) VALUES(?,?,?)", (user_id, "model", ai_text))
            db().commit()
            return ai_text
            
        return "❌ سیستەمی زیرەک نەیتوانی وەڵام بداتەوە."
    except Exception as e:
        return "❌ کێشەیەک لە مێشکی سیستەم ڕوویدا."

def get_vision_ai_response(image_path, user_prompt):
    if not AI_API_KEY: 
        return "❌ کلیل نییە."
    try:
        with open(image_path, "rb") as f: 
            enc = base64.b64encode(f.read()).decode('utf-8')
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={AI_API_KEY}"
        
        prompt_text = "You are an elite frontend developer. Write the complete HTML/CSS code for this UI image. " + user_prompt
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text}, 
                        {"inline_data": {"mime_type": "image/jpeg", "data": enc}}
                    ]
                }
            ]
        }
        
        response = requests.post(url, json=payload, timeout=45)
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            return data['candidates'][0]['content']['parts'][0]['text']
            
        return "❌ نەتوانرا وێنەکە بخوێنرێتەوە."
    except Exception as e:
        return "❌ کێشەیەک لە سیستەمی بینین ڕوویدا."
