from fastapi import FastAPI, Request
import os, httpx

app = FastAPI()
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

print("starting")

@app.get("/webhook")
async def verify(request: Request):
    print("get")
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(q.get("hub.challenge"))

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("\n\n📦 MENSAJE RECIBIDO:")
    print(data)
    
    try:
        value = data["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        to = msg["from"]  # ej: "573154596708"

        url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": "OK"},
        }

        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, headers=headers, json=payload)
            print("📤 SEND:", r.status_code, r.text)

    except Exception as e:
        print("⚠️ No pude responder:", e)

    return {"ok": True}
