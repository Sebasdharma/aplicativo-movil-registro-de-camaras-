from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from database import init_db, get_db, registrar_asistencia_db, obtener_resumen_asistencia
from carchito_voice import CarchitoVoiceAssistant
from face_engine import FaceEngine
import threading

app = Flask(__name__)
CORS(app)

init_db()
asistente = CarchitoVoiceAssistant()
face_engine = FaceEngine()

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BúhoPass - Sistema Inteligente de Asistencia (UPEC)</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #003366;
            --secondary: #0066cc;
            --accent: #00d2ff;
            --bg: #0b132b;
            --card-bg: rgba(255, 255, 255, 0.05);
            --border: rgba(255, 255, 255, 0.1);
            --present: #10b981;
            --absent: #ef4444;
            --late: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }
        body { background: var(--bg); color: #fff; padding: 20px; min-height: 100vh; }
        .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
        .brand { display: flex; align-items: center; gap: 12px; }
        .brand h1 { font-size: 24px; font-weight: 700; color: var(--accent); }
        .brand span { font-size: 13px; color: #94a3b8; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 20px; backdrop-filter: blur(10px); }
        .stat-card h3 { font-size: 13px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; }
        .stat-card .val { font-size: 32px; font-weight: 700; }
        .main-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
        .table-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 24px; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
        th { color: #94a3b8; font-weight: 600; }
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .badge-present { background: rgba(16, 185, 129, 0.2); color: var(--present); border: 1px solid var(--present); }
        .badge-absent { background: rgba(239, 68, 68, 0.2); color: var(--absent); border: 1px solid var(--absent); }
        .badge-late { background: rgba(245, 158, 11, 0.2); color: var(--late); border: 1px solid var(--late); }
        .assistant-card { background: linear-gradient(135deg, rgba(0, 51, 102, 0.4), rgba(0, 102, 204, 0.2)); border: 1px solid var(--border); border-radius: 16px; padding: 24px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .mic-btn { width: 70px; height: 70px; border-radius: 50%; background: var(--secondary); border: none; color: #fff; font-size: 28px; cursor: pointer; display: flex; align-items: center; justify-content: center; margin: 20px 0; box-shadow: 0 0 20px rgba(0, 210, 255, 0.4); transition: transform 0.2s; }
        .mic-btn:hover { transform: scale(1.08); }
        .btn-action { background: #1e293b; border: 1px solid var(--border); color: #fff; padding: 10px 16px; border-radius: 8px; cursor: pointer; margin-top: 10px; width: 100%; font-weight: 600; }
        .btn-action:hover { background: var(--secondary); }
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">
            <div style="font-size: 32px;">🦉</div>
            <div>
                <h1>BúhoPass UPEC</h1>
                <span>Sistema Inteligente de Asistencia Móvil | 7mo AM Computación</span>
            </div>
        </div>
        <div>
            <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600;">● Sistema en Línea</span>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <h3>Materia Activa</h3>
            <div class="val" style="font-size: 20px; color: var(--accent);">Aplicaciones Móviles</div>
            <span style="font-size: 12px; color: #94a3b8;">Docente: Ing. Samuel Lascano</span>
        </div>
        <div class="stat-card">
            <h3>Presentes</h3>
            <div class="val" style="color: var(--present);" id="stat-presentes">0</div>
        </div>
        <div class="stat-card">
            <h3>Ausentes</h3>
            <div class="val" style="color: var(--absent);" id="stat-ausentes">0</div>
        </div>
        <div class="stat-card">
            <h3>Porcentaje Asistencia</h3>
            <div class="val" style="color: var(--accent);" id="stat-porcentaje">0%</div>
        </div>
    </div>

    <div class="main-layout">
        <div class="table-card">
            <h2>Registro en Vivo de Estudiantes</h2>
            <table>
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Estudiante</th>
                        <th>Estado</th>
                        <th>Hora</th>
                        <th>Método</th>
                        <th>Acción Manual</th>
                    </tr>
                </thead>
                <tbody id="lista-estudiantes">
                    <!-- Dinámico -->
                </tbody>
            </table>
        </div>

        <div class="assistant-card">
            <h2>Asistente "Carchito"</h2>
            <p style="color: #94a3b8; font-size: 14px; margin-top: 6px;">Comandos por voz y reconocimiento facial en vivo</p>
            <button class="mic-btn" onclick="activarVoz()">🎤</button>
            <div id="voz-estado" style="font-size: 13px; color: var(--accent); margin-bottom: 12px;">Haz clic para hablar a Carchito</div>
            <button class="btn-action" onclick="activarCamara()">📷 Iniciar Cámara / Escaneo Facial</button>
            <button class="btn-action" style="background: rgba(16, 185, 129, 0.2); border-color: var(--present);" onclick="actualizarDatos()">🔄 Actualizar Lista</button>
        </div>
    </div>

    <script>
        async function actualizarDatos() {
            try {
                const res = await fetch('/api/asistencia/resumen?materia_id=1');
                const data = await res.json();
                const tbody = document.getElementById('lista-estudiantes');
                tbody.innerHTML = '';
                
                let presentes = 0;
                let ausentes = 0;
                
                data.forEach(est => {
                    if (est.estado === 'Presente') presentes++;
                    else ausentes++;
                    
                    const badgeClass = est.estado === 'Presente' ? 'badge-present' : 'badge-absent';
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${est.codigo_estudiantil}</strong></td>
                        <td>${est.nombre_completo}</td>
                        <td><span class="badge ${badgeClass}">${est.estado}</span></td>
                        <td>${est.hora}</td>
                        <td style="color: #94a3b8; font-size: 12px;">${est.metodo}</td>
                        <td>
                            <button style="background: none; border: 1px solid var(--border); color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer;" onclick="marcarManual(${est.id}, '${est.estado === 'Presente' ? 'Ausente' : 'Presente'}')">
                                ${est.estado === 'Presente' ? 'Marcar Ausente' : 'Marcar Presente'}
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
                
                document.getElementById('stat-presentes').innerText = presentes;
                document.getElementById('stat-ausentes').innerText = ausentes;
                const total = presentes + ausentes;
                document.getElementById('stat-porcentaje').innerText = total > 0 ? Math.round((presentes / total) * 100) + '%' : '0%';
            } catch(e) {
                console.error(e);
            }
        }

        async function marcarManual(estudianteId, nuevoEstado) {
            await fetch('/api/asistencia/manual', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ estudiante_id: estudianteId, materia_id: 1, estado: nuevoEstado })
            });
            actualizarDatos();
        }

        async function activarCamara() {
            document.getElementById('voz-estado').innerText = "Iniciando cámara...";
            await fetch('/api/camara/iniciar', { method: 'POST' });
        }

        function activarVoz() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                alert("Tu navegador no soporta SpeechRecognition. Puedes usar el botón de cámara o Chrome.");
                return;
            }
            const recognition = new SpeechRecognition();
            recognition.lang = 'es-EC';
            document.getElementById('voz-estado').innerText = "Escuchando... di 'Hola Carchito, toma asistencia'";
            recognition.start();
            
            recognition.onresult = async (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('voz-estado').innerText = `Dijiste: "${transcript}"`;
                const res = await fetch('/api/carchito/comando', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ comando: transcript, materia_id: 1 })
                });
                const data = await res.json();
                actualizarDatos();
            };
        }

        setInterval(actualizarDatos, 3000);
        actualizarDatos();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route("/api/asistencia/resumen", methods=["GET"])
def api_resumen():
    materia_id = request.args.get("materia_id", 1, type=int)
    return jsonify(obtener_resumen_asistencia(materia_id))

@app.route("/api/asistencia/manual", methods=["POST"])
def api_manual():
    data = request.json
    est_id = data.get("estudiante_id")
    mat_id = data.get("materia_id", 1)
    estado = data.get("estado", "Presente")
    res = registrar_asistencia_db(est_id, mat_id, estado=estado, metodo="Manual-Docente")
    return jsonify(res)

@app.route("/api/carchito/comando", methods=["POST"])
def api_comando():
    data = request.json
    comando = data.get("comando", "")
    mat_id = data.get("materia_id", 1)
    res = asistente.procesar_comando(comando, mat_id)
    return jsonify(res)

@app.route("/api/camara/iniciar", methods=["POST"])
def api_camara():
    threading.Thread(target=face_engine.ejecutar_camara_en_vivo, args=(1,), daemon=True).start()
    return jsonify({"status": "ok", "mensaje": "Cámara de reconocimiento facial iniciada"})

if __name__ == "__main__":
    print("Iniciando Servidor BúhoPass UPEC en http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
