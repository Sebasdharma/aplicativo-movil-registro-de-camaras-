import cv2
import os
from database import init_db, get_db

def enrolar_estudiante_camara(codigo, nombre, paralelo="7mo Semestre - Paralelo AM"):
    init_db()
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_estudiantes")
    os.makedirs(dataset_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara.")
        return
        
    print(f"\n=======================================================")
    print(f" ENROLAMIENTO FACIAL BÚHOPASS: {nombre} ({codigo})")
    print(f"=======================================================")
    print("Mire a la cámara. Presione 'ESPACIO' para capturar la foto base o 'ESC' para cancelar.\n")
    
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    foto_guardada = False
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        display_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(100, 100))
        
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 210, 255), 2)
            cv2.putText(display_frame, "Rostro detectado - Presione ESPACIO", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 210, 255), 1)
                        
        cv2.imshow("Enrolamiento Facial BúhoPass - UPEC", display_frame)
        key = cv2.waitKey(1)
        
        if key == 32: # Barra espaciadora
            foto_filename = f"{codigo}.jpg"
            foto_path = os.path.join(dataset_dir, foto_filename)
            cv2.imwrite(foto_path, frame)
            
            # Guardar o actualizar en SQLite
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM estudiantes WHERE codigo_estudiantil = ?", (codigo,))
            existe = cursor.fetchone()
            if existe:
                cursor.execute("UPDATE estudiantes SET nombre_completo = ?, foto_path = ? WHERE id = ?", (nombre, foto_filename, existe['id']))
            else:
                cursor.execute("INSERT INTO estudiantes (codigo_estudiantil, nombre_completo, nivel_paralelo, foto_path) VALUES (?, ?, ?, ?)",
                               (codigo, nombre, paralelo, foto_filename))
            conn.commit()
            conn.close()
            
            print(f"\n[ÉXITO] Foto de {nombre} guardada en: {foto_path}")
            print("¡Estudiante enrolado exitosamente en el sistema BúhoPass!")
            foto_guardada = True
            break
        elif key == 27: # ESC
            print("Enrolamiento cancelado.")
            break
            
    cap.release()
    cv2.destroyAllWindows()
    return foto_guardada

if __name__ == "__main__":
    import sys
    print("=== MÓDULO DE ENROLAMIENTO FACIAL BÚHOPASS ===")
    nombre = input("Ingrese el Nombre Completo del Estudiante: ").strip() or "Reina Gordon Jhoel Sebastian"
    codigo = input("Ingrese el Código Estudiantil (ej. UPEC-2026-001): ").strip() or "UPEC-2026-001"
    enrolar_estudiante_camara(codigo, nombre)
