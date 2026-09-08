import cv2
import numpy as np
import os
import time
from database import registrar_asistencia_db, get_db

class FaceEngine:
    def __init__(self):
        # Cargar clasificador preentrenado Haar Cascade para detección frontal
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Mapeo de estudiantes registrados
        self.estudiantes = [
            {"id": 1, "nombre": "Reina Gordon Jhoel Sebastian", "codigo": "UPEC-2026-001"},
            {"id": 2, "nombre": "Cadena Edelina", "codigo": "UPEC-2026-002"},
            {"id": 3, "nombre": "Lema Jordy", "codigo": "UPEC-2026-003"},
            {"id": 4, "nombre": "Ponce Melisa", "codigo": "UPEC-2026-004"}
        ]
        self.ultimo_registro = {}
        
    def procesar_frame(self, frame, materia_id=1):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))
        
        resultados = []
        for idx, (x, y, w, h) in enumerate(faces):
            # Simulación de emparejamiento con el estudiante identificado en el prototipo
            est_idx = idx % len(self.estudiantes)
            estudiante = self.estudiantes[est_idx]
            
            # Control de frecuencia (evitar spam de registros en segundos continuos)
            ahora = time.time()
            if estudiante["id"] not in self.ultimo_registro or (ahora - self.ultimo_registro[estudiante["id"]]) > 10:
                registrar_asistencia_db(estudiante["id"], materia_id, estado="Presente", metodo="Facial-Carchito")
                self.ultimo_registro[estudiante["id"]] = ahora
                
            # Dibujar recuadro verde y nombre sobre el frame
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{estudiante['nombre']} ({estudiante['codigo']})", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cv2.putText(frame, "PRESENTE - REGISTRADO", (x, y + h + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            resultados.append({
                "estudiante_id": estudiante["id"],
                "nombre": estudiante["nombre"],
                "codigo": estudiante["codigo"],
                "bbox": [int(x), int(y), int(w), int(h)]
            })
            
        return frame, resultados

    def ejecutar_camara_en_vivo(self, materia_id=1):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("No se pudo acceder a la cámara web.")
            return
            
        print("Iniciando escaneo facial BúhoPass... Presiona 'q' para salir.")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_proc, resultados = self.procesar_frame(frame, materia_id)
            cv2.imshow("BúhoPass - Reconocimiento Facial en Vivo (UPEC)", frame_proc)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    from database import init_db
    init_db()
    engine = FaceEngine()
    engine.ejecutar_camara_en_vivo()
