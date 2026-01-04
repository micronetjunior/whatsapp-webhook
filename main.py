from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os
import httpx

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "verify_token_default")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

async def send_whatsapp_text(to: str, text: str):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("❌ Faltan variables WHATSAPP_TOKEN o PHONE_NUMBER_ID")
        return

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        print("📤 SEND:", r.status_code, r.text)

@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
        and params.get("hub.challenge")
    ):
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Invalid verification token", status_code=403)

@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    print("📩 Mensaje recibido:", body)

    try:
        value = body["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        from_number = msg["from"]

        if msg.get("type") == "text":
            text = msg["text"]["body"]
        else:
            text = f"[Recibí mensaje tipo {msg.get('type')}]"

        await send_whatsapp_text(from_number, f"Recibí: {text}")

    except Exception as e:
        print("⚠️ No pude procesar el mensaje:", e)

    return {"status": "ok"}
