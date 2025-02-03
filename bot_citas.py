import os
import time
from playwright.sync_api import sync_playwright
import requests
import hashlib

TELEGRAM_TOKEN = os.getenv("7487783707:AAHBIlyKLWsELyQkk8uI35xWeWaU3EYPeJA")
CHAT_ID = os.getenv("1022714311")
URL_INICIAL = "https://www.exteriores.gob.es/Consulados/lahabana/es/ServiciosConsulares/Paginas/index.aspx?scca=Certificados&scco=Cuba&scd=166&scs=Certificado+de+nacimiento"
URL_CITAS = "https://www.citaconsular.es/es/hosteds/widgetdefault/2f21cd9c0d8aa26725bf8930e4691d645/bkt177628"
CHECK_INTERVAL = 60  # Segundos entre verificaciones
ERROR_INTERVAL = 60  # Segundos tras error

def send_alert(message):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
    )

def get_content_hash(content):
    return hashlib.sha256(content.encode()).hexdigest()

def check_availability():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        try:
            # Paso 1: Cargar página inicial para establecer cookies
            page = context.new_page()
            page.goto(URL_INICIAL, wait_until="networkidle")
            
            # Paso 2: Navegar a la página de citas
            page.goto(URL_CITAS, wait_until="networkidle")
            
            # Paso 3: Manejar el botón OK si existe
            try:
                page.wait_for_selector("button:has-text('OK')", timeout=5000)
                page.click("button:has-text('OK')")
                # Esperar a que se recargue el contenido
                page.wait_for_load_state("networkidle")
            except:
                pass  # Si no hay botón, continuar
            
            # Paso 4: Obtener contenido actualizado
            content = page.inner_text("body")
            current_hash = get_content_hash(content)
            
            # Paso 5: Verificar disponibilidad
            if "No hay citas disponibles" not in content:
                send_alert("<b>🚨 CITAS DISPONIBLES!</b>\n¡Reserva ahora!")
                return True, current_hash
                
            return False, current_hash
            
        except Exception as e:
            send_alert(f"⚠️ Error en el sistema:\n<code>{str(e)}</code>")
            return None, None
        finally:
            context.close()
            browser.close()

def main():
    last_hash = None
    
    while True:
        try:
            start_time = time.time()
            
            # Ejecutar verificación
            status, new_hash = check_availability()
            
            if status is True:
                # Si hay citas, mantener hash para evitar repeticiones
                last_hash = new_hash
            elif status is False and new_hash != last_hash:
                # Notificar cambio de estado (aunque no haya disponibilidad)
                send_alert("🔄 Estado actualizado (sin citas disponibles)")
                last_hash = new_hash
            
            # Calcular tiempo restante para cumplir con el intervalo
            elapsed = time.time() - start_time
            sleep_time = max(CHECK_INTERVAL - elapsed, 5)
            time.sleep(sleep_time)
            
        except Exception as e:
            send_alert(f"⛔ Error crítico:\n<code>{str(e)}</code>")
            time.sleep(ERROR_INTERVAL)

if name == "main":
    send_alert("🤖 Bot iniciado correctamente\nMonitoreando 24/7")
    main()