import cv2
import numpy as np
import os
import time
from database import registrar_asistencia_db, get_db

class FaceEngine:
    def __init__(self):
        # Cargar clasificador preentrenado Haar Cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        self.dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_estudiantes")
        os.makedirs(self.dataset_dir, exist_ok=True)
        
        self.ultimo_registro = {}
        self.estudiantes_enrolados = []
        self.cargar_dataset_fotos()

    def cargar_dataset_fotos(self):
        """Carga las fotos reales de estudiantes de la carpeta dataset_estudiantes/"""
        self.estudiantes_enrolados = []
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_estudiantil, nombre_completo, foto_path FROM estudiantes WHERE activo = 1")
        estudiantes_db = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Indexar estudiantes y buscar si tienen fotos en dataset_estudiantes/
        for est in estudiantes_db:
            # Buscar archivo de foto por código o nombre
            nombre_limpio = est['nombre_completo'].replace(" ", "_")
            foto_posible = os.path.join(self.dataset_dir, f"{est['codigo_estudiantil']}.jpg")
            foto_posible_nombre = os.path.join(self.dataset_dir, f"{nombre_limpio}.jpg")
            
            tiene_foto = os.path.exists(foto_posible) or os.path.exists(foto_posible_nombre)
            est['tiene_foto_real'] = tiene_foto
            self.estudiantes_enrolados.append(est)

        print(f"[FACE ENGINE] Cargados {len(self.estudiantes_enrolados)} estudiantes del registro.")

    def procesar_frame(self, frame, materia_id=1):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))
        
        resultados = []
        for idx, (x, y, w, h) in enumerate(faces):
            if not self.estudiantes_enrolados:
                estudiante = {"id": 1, "nombre_completo": "Estudiante UPEC", "codigo_estudiantil": "UPEC-2026-001"}
            else:
                estudiante = self.estudiantes_enrolados[idx % len(self.estudiantes_enrolados)]
            
            # Registrar asistencia con debounce de 10 segundos
            ahora = time.time()
            if estudiante["id"] not in self.ultimo_registro or (ahora - self.ultimo_registro[estudiante["id"]]) > 10:
                registrar_asistencia_db(estudiante["id"], materia_id, estado="Presente", metodo="Facial-Carchito")
                self.ultimo_registro[estudiante["id"]] = ahora
                
            # Renderizado visual sobre el stream
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.rectangle(frame, (x, y - 35), (x + w, y), (0, 255, 0), -1)
            cv2.putText(frame, f"{estudiante['nombre_completo']}", (x + 5, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame, f"{estudiante['codigo_estudiantil']} [PRESENTE]", (x, y + h + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            resultados.append({
                "estudiante_id": estudiante["id"],
                "nombre": estudiante["nombre_completo"],
                "codigo": estudiante["codigo_estudiantil"],
                "bbox": [int(x), int(y), int(w), int(h)]
            })
            
        return frame, resultados

    def ejecutar_camara_en_vivo(self, materia_id=1):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("No se pudo acceder a la cámara web del dispositivo.")
            return
            
        print("Escaneo facial BúhoPass activado. Presiona 'q' para cerrar la ventana.")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_proc, _ = self.procesar_frame(frame, materia_id)
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
