from fastapi import FastAPI, Request
import os
import requests

app = FastAPI()

META_TOKEN = os.getenv("META_TOKEN")
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
WABA_ID = os.getenv("WABA_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("📩 ENTRANTE:", data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        text = message["text"]["body"]

        print(f"Mensaje de {from_number}: {text}")

        send_message(from_number, "Hola 👋")

    except Exception as e:
        print("No es un mensaje de texto:", e)

    return {"ok": True}


def send_message(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {VERIFY_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }

    r = requests.post(url, json=payload, headers=headers)
    print("📤 RESPUESTA META:", r.status_code, r.text)
