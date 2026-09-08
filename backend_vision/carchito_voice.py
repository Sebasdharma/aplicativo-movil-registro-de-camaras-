import threading
import time

class CarchitoVoiceAssistant:
    def __init__(self):
        self.nombre = "Carchito"
        self.activo = False
        
    def hablar(self, mensaje):
        print(f"\n[ASISTENTE CARCHITO]: \"{mensaje}\"")
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(mensaje)
            engine.runAndWait()
        except Exception as e:
            # Fallback en caso de que pyttsx3 no esté inicializado
            pass

    def procesar_comando(self, texto_comando, materia_id=1):
        texto = texto_comando.lower().strip()
        print(f"[COMANDO RECIBIDO]: '{texto}'")
        
        if "hola carchito" in texto or "carchito" in texto:
            if "toma lista" in texto or "asistencia" in texto or "inicia" in texto or "registrar" in texto:
                self.hablar("Hola docente. Iniciando el sistema de escaneo facial para la clase de Aplicaciones Móviles.")
                return {"accion": "iniciar_escaneo", "mensaje": "Escaneo facial activado."}
            elif "reporte" in texto or "resumen" in texto or "cuántos" in texto:
                self.hablar("Consultando la asistencia del aula. Tienes el reporte listo en tu aplicación móvil.")
                return {"accion": "consultar_reporte", "mensaje": "Reporte generado en pantalla."}
            else:
                self.hablar("Hola, soy Carchito, tu asistente de asistencia UPEC. ¿Qué deseas hacer?")
                return {"accion": "saludo", "mensaje": "Asistente Carchito listo."}
        else:
            return {"accion": "desconocido", "mensaje": "Comando no reconocido."}

if __name__ == "__main__":
    asistente = CarchitoVoiceAssistant()
    asistente.hablar("Hola Sebastián y equipo. Soy Carchito, su asistente de asistencia virtual de la UPEC.")
