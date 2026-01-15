from fastapi import FastAPI, Request, Query, Response
from fastapi.responses import PlainTextResponse
import openai
import os
import requests
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER
import redis
import json

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
META_TOKEN = os.getenv("META_TOKEN")
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WABA_ID = os.getenv("WABA_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDISHOST = os.getenv("REDISHOST")
REDISPORT = os.getenv("REDISPORT")
REDISPASSWORD = os.getenv("REDIS_PASAWORD")

r = redis.Redis(
    host=REDISHOST,
    port=REDISPORT,
    password=REDISPASSWORD,
    decode_responses=True
)

# -------------------------------
# VERIFICACIÓN DEL WEBHOOK (GET)
# -------------------------------
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, status_code=200)

    return Response(status_code=403)

# -------------------------------
# RECEPCIÓN DE MENSAJES (POST)
# -------------------------------
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    print("📩 Evento recibido de Meta:")

    try:
    
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # 📨 MENSAJE DEL USUARIO
        if "messages" in value:
            messages = value["messages"][0]
            print("payload",messages)
            
            from_number=messages["from"]
            text=messages["text"]["body"]
            
            # Procesamiento
            reply_text = procesar_mensaje(messages,from_number)
            #print(reply_text)
            
            print(f"📨 Mensaje de {from_number}: {text}")
            # Responder
            print("Se procede a remitir respuesta a",from_number)
            enviar_mensaje(from_number,reply_text)
        
        # 📬 STATUS (delivered, read, etc.)
        elif "statuses" in value:
            statuses = value["statuses"]
            print("STATUS:", statuses)
        else:
            print("Evento no reconocido")

    except Exception as e:
        print("Try de metodo post ❌ Error procesando mensaje:", e)

    # Meta necesita 200 SIEMPRE
    return Response(status_code=200)


# -------------------------------
# LÓGICA DEL MENSAJE
# -------------------------------
def procesar_mensaje(texto: list,telefono: str) -> list:
    saludo = ["hola", "buenas", "como estas", "buenas tardes"]
    palabras_duda = ["duda", "pregunta", "consulta", "no entiendo", "ayuda","?"]
    
    #texto_lower = texto[0]["text"]["body"].lower()#para dict
    texto_lower = texto.get("text", {}).get("body").lower()
    
    # Detectar saludos
    if any(palabra in texto_lower for palabra in saludo):
        print("saludo")
        return "Hola 👋 ¿Cómo puedo ayudarte?"
    # Detectar si es una duda o pregunta
    elif any(palabra in texto_lower for palabra in palabras_duda):
        print("procesar IA")
        respuestaIA = procesarIA(texto_lower)

        guardar_estado(
            telefono,
            "ESPERANDO_CONFIRMACION_PDF",
            {"texto": respuestaIA}
        )
        
        enviar_mensaje(
            telefono,
            "¿Deseas recibir esta información en PDF? Responde SI o NO"
        )

        return respuestaIA # Solo procesa IA si es una duda
    else:
    # Si no es saludo ni duda, pedimos que escriba la pregunta completa
        return "Por favor, escribe tu duda o pregunta completa para poder ayudarte."

# -------------------------------
# PROCESAMIETO CON IA
# -------------------------------

openai.api_key = OPENAI_API_KEY
print(OPENAI_API_KEY)

def procesarIA(solicitud: str, modelo: str = "gpt-4o-mini") -> str:
    """
    Procesa un texto usando la API moderna de OpenAI ChatCompletion.
    """
    print("solicitud:",solicitud)
    try:
        print("vamo al openIA")
        response = openai.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": solicitud}],
            max_tokens=1000,
            temperature=0.7
        )
        respuesta = response.choices[0].message.content
        print("respuesta:",respuesta)
        return respuesta
    except Exception as e:
        print("error en try de OpenAI")
        return f"Try openAI, Error procesando la solicitud: {e}"

def enviar_mensaje(to: str, message: str):
    url = f"https://graph.facebook.com/v24.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization":f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type":"application/json"
    }

    payload = {
        "messaging_product":"whatsapp",
        "to":to,
        "text":{"body":message}
    }

    response = requests.post(url, headers=headers, json=payload)

    print("📤 Respuesta enviada:", response.status_code, response.text)

def generar_pdf_bytes(texto: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()

    texto = texto.replace("\n", "<br/>")
    doc.build([Paragraph(texto, styles["Normal"])])

    buffer.seek(0)
    return buffer.read()

def subir_pdf_whatsapp(pdf_bytes: bytes, token: str, phone_number_id: str) -> str:
    url = f"https://graph.facebook.com/v24.0/{phone_number_id}/media"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    files = {
        "file": ("respuesta.pdf", pdf_bytes, "application/pdf"),
        "type": (None, "application/pdf"),
        "messaging_product": (None, "whatsapp")
    }

    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()

    return response.json()["id"]
    
def enviar_pdf_whatsapp(media_id: str, to: str, token: str, phone_number_id: str):
    url = f"https://graph.facebook.com/v24.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": "respuesta_ia.pdf"
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
def guardar_estado(telefono, estado, data=None, ttl=600):
    payload = {
        "estado": estado,
        "data": data
    }
    r.setex(f"user:{telefono}", ttl, json.dumps(payload))
    
def obtener_estado(telefono):
    data = r.get(f"user:{telefono}")
    return json.loads(data) if data else None