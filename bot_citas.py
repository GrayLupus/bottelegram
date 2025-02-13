import os
import time
import threading
from flask import Flask
from playwright.sync_api import sync_playwright
import requests
import hashlib

app = Flask(__name__)

# Configuración desde variables de entorno
TELEGRAM_TOKEN = os.getenv("7487783707:AAHBIlyKLWsELyQkk8uI35xWeWaU3EYPeJA")
CHAT_ID = os.getenv("1022714311")
URL_INICIAL = os.getenv("https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scca=Notar%C3%ADa&scco=Cuba&scd=166&scs=Otras+escrituras")
URL_CITAS = os.getenv("https://www.citaconsular.es/es/hosteds/widgetdefault/2f21cd9c0d8aa26725bf8930e4691d645/bkt177496")
CHECK_INTERVAL = 60
ERROR_INTERVAL = 300

# Estado compartido
last_check_time = None
last_status = None
current_status = "Monitoreo iniciando..."

def send_message(chat_id, text, parse_mode="HTML"):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    )

def check_availability():
    global last_check_time, last_status, current_status
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        try:
            page = context.new_page()
            page.goto(URL_INICIAL, wait_until="networkidle")
            page.goto(URL_CITAS, wait_until="networkidle")
            
            # Click en botones OK y Continuar
            for btn in ["Aceptar", "Continue / Continuar"]:
                try:
                    page.click(f"button:has-text('{btn}')", timeout=5000)
                    page.wait_for_load_state("networkidle")
                except:
                    pass
            
            content = page.inner_text("body")
            current_hash = hashlib.sha256(content.encode()).hexdigest()
            
            if "No hay citas disponibles" not in content:
                send_message(CHAT_ID, "<b>🚨 CITAS DISPONIBLES!</b>\n¡Reserva ahora!")
                current_status = "Citas disponibles"
                return True, current_hash
                
            current_status = "Sin citas disponibles"
            return False, current_hash
            
        except Exception as e:
            current_status = f"Error: {str(e)}"
            send_message(CHAT_ID, f"⚠️ Error en el sistema:\n<code>{str(e)}</code>")
            return None, None
        finally:
            context.close()
            browser.close()

def monitor_loop():
    global last_check_time, last_status
    while True:
        try:
            start_time = time.time()
            status, new_hash = check_availability()
            last_check_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
            if status is True or (status is False and new_hash != last_status):
                last_status = new_hash
                
            time.sleep(max(CHECK_INTERVAL - (time.time() - start_time), 5))
            
        except Exception as e:
            send_message(CHAT_ID, f"⛔️ Error crítico:\n<code>{str(e)}</code>")
            time.sleep(ERROR_INTERVAL)

def get_updates():
    offset = None
    while True:
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30}
            )
            updates = response.json().get("result", [])
            
            for update in updates:
                offset = update["update_id"] + 1
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")
                    
                    if "/start" in text:
                        send_message(chat_id, "🤖 Bot de citas activo\nMonitoreo 24/7 con Koyeb")
                        
                    elif "/status" in text:
                        status_msg = f"Última verificación: {last_check_time}\nEstado actual: {current_status}"
                        send_message(chat_id, status_msg)
        
        except Exception as e:
            print(f"Error obteniendo actualizaciones: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Iniciar monitor en segundo plano
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Iniciar el loop de actualizaciones de Telegram
    updates_thread = threading.Thread(target=get_updates, daemon=True)
    updates_thread.start()
    
    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))