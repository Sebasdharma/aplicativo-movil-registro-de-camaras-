package com.upec.asistech.j2camera;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.graphics.YuvImage;
import android.hardware.Camera;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Base64;
import android.util.Log;
import android.view.Gravity;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

@SuppressWarnings("deprecation")
public final class MainActivity extends Activity implements SurfaceHolder.Callback {
    private static final String PREFS = "asistech_j2_camera";
    private static final String TABLET_ID_KEY = "tablet_id";
    private static final String TABLET_ID_PREFIX = "j2-aula-";
    private static final String TABLET_NAME = "Galaxy J2 Aula";
    private static final long HEARTBEAT_INTERVAL_MS = 2000;
    private static final long FRAME_INTERVAL_MS = 1000;
    private static final long SCAN_DURATION_MS = 10 * 60 * 1000L;
    private static final int CAMERA_PERMISSION_REQUEST = 41;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService networkExecutor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean heartbeatInFlight = new AtomicBoolean(false);
    private final AtomicBoolean frameInFlight = new AtomicBoolean(false);
    private final AtomicBoolean previewFrameConfirmed = new AtomicBoolean(false);
    private final AtomicBoolean active = new AtomicBoolean(false);

    private TextView statusView;
    private TextView resultView;
    private TextView cameraPlaceholder;
    private SurfaceView previewView;
    private SurfaceHolder surfaceHolder;
    private WifiManager.WifiLock wifiLock;
    private Camera camera;
    private Camera.CameraInfo activeCameraInfo;
    private String tabletId;
    private int materiaId;
    private long scanDeadline;
    private long lastFrameAt;
    private volatile long lastPreviewFrameAt;
    private String lastResultKey = "";
    private int previewWidth;
    private int previewHeight;
    private int previewRestartAttempts;
    private boolean surfaceReady;
    private boolean waitingForCameraPermission;

    private final Runnable heartbeatLoop = new Runnable() {
        @Override
        public void run() {
            sendHeartbeat();
            mainHandler.postDelayed(this, HEARTBEAT_INTERVAL_MS);
        }
    };

    private final Runnable scanTimeout = new Runnable() {
        @Override
        public void run() {
            if (!active.get()) {
                return;
            }
            if (SystemClock.elapsedRealtime() >= scanDeadline) {
                stopScan("Escaneo finalizado. Esperando una nueva orden.");
            } else {
                mainHandler.postDelayed(this, 1000);
            }
        }
    };

    private final Runnable previewWatchdog = new Runnable() {
        @Override
        public void run() {
            if (!active.get() || camera == null) {
                return;
            }
            if (SystemClock.elapsedRealtime() - lastPreviewFrameAt > 5000) {
                if (previewRestartAttempts == 0) {
                    previewRestartAttempts++;
                    restartPreview();
                    return;
                }
                stopScan("La cámara no entrega imagen. Revisa el lente y vuelve a iniciar.");
                return;
            }
            mainHandler.postDelayed(this, 5000);
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        configureDisplay();
        tabletId = getTabletId();
        buildScreen();
        startLockTask();

        WifiManager wifiManager = (WifiManager) getApplicationContext()
                .getSystemService(Context.WIFI_SERVICE);
        if (wifiManager != null) {
            wifiLock = wifiManager.createWifiLock(
                    WifiManager.WIFI_MODE_FULL_HIGH_PERF,
                    "AsisTechJ2Camera:heartbeat");
            wifiLock.setReferenceCounted(false);
        }
        acquireWifiLock();
        mainHandler.post(heartbeatLoop);
    }

    private void configureDisplay() {
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        WindowManager.LayoutParams attributes = window.getAttributes();
        attributes.screenBrightness = 0.18f;
        window.setAttributes(attributes);
        window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN);
    }

    private void buildScreen() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(244, 247, 245));
        root.setPadding(dp(20), dp(18), dp(20), dp(18));

        TextView title = new TextView(this);
        title.setText("ASISTECH · CÁMARA");
        title.setTextColor(Color.rgb(0, 107, 60));
        title.setTextSize(21);
        title.setGravity(Gravity.CENTER);
        title.setPadding(0, dp(8), 0, dp(8));
        root.addView(title, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        statusView = new TextView(this);
        statusView.setText("Conectando y esperando una orden…");
        statusView.setTextColor(Color.rgb(35, 54, 44));
        statusView.setTextSize(16);
        statusView.setGravity(Gravity.CENTER);
        statusView.setPadding(0, dp(12), 0, dp(8));
        root.addView(statusView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        resultView = new TextView(this);
        resultView.setText("");
        resultView.setTextColor(Color.rgb(0, 107, 60));
        resultView.setTextSize(20);
        resultView.setGravity(Gravity.CENTER);
        root.addView(resultView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(42)));

        cameraPlaceholder = new TextView(this);
        cameraPlaceholder.setText("La cámara se activará al iniciar el escaneo.");
        cameraPlaceholder.setTextColor(Color.GRAY);
        cameraPlaceholder.setTextSize(15);
        cameraPlaceholder.setGravity(Gravity.CENTER);
        root.addView(cameraPlaceholder, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        previewView = new SurfaceView(this);
        previewView.setBackgroundColor(Color.BLACK);
        previewView.setVisibility(View.GONE);
        surfaceHolder = previewView.getHolder();
        surfaceHolder.setType(SurfaceHolder.SURFACE_TYPE_PUSH_BUFFERS);
        surfaceHolder.addCallback(this);
        root.addView(previewView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        TextView footer = new TextView(this);
        footer.setText("Cámara frontal · Se detiene automáticamente en 10 minutos");
        footer.setTextColor(Color.DKGRAY);
        footer.setTextSize(12);
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, dp(10), 0, 0);
        root.addView(footer, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        setContentView(root);
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private String getTabletId() {
        SharedPreferences preferences = getSharedPreferences(PREFS, MODE_PRIVATE);
        String saved = preferences.getString(TABLET_ID_KEY, null);
        if (saved != null && !saved.isEmpty()) {
            return saved;
        }
        String generated = TABLET_ID_PREFIX
                + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        preferences.edit().putString(TABLET_ID_KEY, generated).apply();
        return generated;
    }

    @Override
    protected void onResume() {
        super.onResume();
        acquireWifiLock();
        if (surfaceReady && active.get() && camera == null) {
            openFrontCamera();
        }
    }

    @Override
    protected void onDestroy() {
        mainHandler.removeCallbacksAndMessages(null);
        closeCamera();
        if (wifiLock != null && wifiLock.isHeld()) {
            wifiLock.release();
        }
        networkExecutor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        showStatus("La cámara queda lista para recibir órdenes del docente.");
    }

    private void acquireWifiLock() {
        if (wifiLock != null && !wifiLock.isHeld()) {
            wifiLock.acquire();
        }
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        surfaceReady = true;
        if (active.get()) {
            openFrontCamera();
        }
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        if (camera != null) {
            camera.stopPreview();
            try {
                camera.setPreviewDisplay(holder);
                camera.startPreview();
            } catch (IOException | RuntimeException error) {
                showStatus("No se pudo mostrar la cámara. Esperando otra orden.");
                stopScan("Cámara no disponible.");
            }
        }
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        surfaceReady = false;
        closeCamera();
    }

    private void sendHeartbeat() {
        if (!heartbeatInFlight.compareAndSet(false, true)) {
            return;
        }
        networkExecutor.execute(() -> {
            try {
                JSONObject payload = new JSONObject();
                payload.put("tablet_id", tabletId);
                payload.put("nombre", TABLET_NAME);
                payload.put("activa", active.get());
                JSONObject response = postJson("/api/camara/tablet/heartbeat", payload);
                JSONObject command = response.optJSONObject("command");
                if (command != null) {
                    handleCommand(command);
                } else if (response.optString("status").equals("ok") && !active.get()) {
                    showStatus("Conectado · esperando la orden del docente.");
                }
            } catch (Exception error) {
                showStatus("Sin conexión con el servidor. Reintentando…");
            } finally {
                heartbeatInFlight.set(false);
            }
        });
    }

    private void handleCommand(JSONObject command) {
        String action = command.optString("action");
        if ("iniciar".equals(action)) {
            int requestedMateriaId = command.optInt("materia_id", 0);
            if (requestedMateriaId > 0 && active.compareAndSet(false, true)) {
                materiaId = requestedMateriaId;
                scanDeadline = SystemClock.elapsedRealtime() + SCAN_DURATION_MS;
                lastResultKey = "";
                previewFrameConfirmed.set(false);
                previewRestartAttempts = 0;
                mainHandler.post(() -> {
                    resultView.setText("");
                    cameraPlaceholder.setVisibility(View.GONE);
                    previewView.setVisibility(View.VISIBLE);
                    showStatus("Escaneo activo · máximo 10 minutos.");
                    prepareCameraForScan();
                    mainHandler.removeCallbacks(scanTimeout);
                    mainHandler.post(scanTimeout);
                });
            }
        } else if ("detener".equals(action) && active.get()) {
            mainHandler.post(() -> stopScan("El docente detuvo el escaneo."));
        }
    }

    private void prepareCameraForScan() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                && checkSelfPermission(Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            waitingForCameraPermission = true;
            requestPermissions(
                    new String[]{Manifest.permission.CAMERA},
                    CAMERA_PERMISSION_REQUEST);
            return;
        }
        if (surfaceReady) {
            openFrontCamera();
        } else {
            showStatus("Preparando la cámara frontal…");
        }
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST || !waitingForCameraPermission) {
            return;
        }
        waitingForCameraPermission = false;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            if (surfaceReady && active.get()) {
                openFrontCamera();
            }
        } else {
            stopScan("Se necesita permiso de cámara para escanear.");
        }
    }

    private void openFrontCamera() {
        if (camera != null || !active.get() || !surfaceReady) {
            return;
        }
        try {
            int cameraId = findFrontCamera();
            if (cameraId < 0) {
                stopScan("No se encontró una cámara frontal.");
                return;
            }
            activeCameraInfo = new Camera.CameraInfo();
            Camera.getCameraInfo(cameraId, activeCameraInfo);
            camera = Camera.open(cameraId);

            Camera.Parameters parameters = camera.getParameters();
            Camera.Size previewSize = selectPreviewSize(parameters);
            if (previewSize != null) {
                parameters.setPreviewSize(previewSize.width, previewSize.height);
            }
            parameters.setPreviewFormat(ImageFormat.NV21);
            if (!parameters.getSupportedPreviewFormats().contains(ImageFormat.NV21)) {
                throw new IOException("La cámara no ofrece el formato de imagen NV21.");
            }
            if (parameters.getSupportedFocusModes().contains(
                    Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO)) {
                parameters.setFocusMode(Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO);
            }
            camera.setParameters(parameters);
            camera.setDisplayOrientation(getDisplayOrientation(activeCameraInfo));
            camera.setPreviewDisplay(surfaceHolder);
            previewWidth = parameters.getPreviewSize().width;
            previewHeight = parameters.getPreviewSize().height;
            camera.setErrorCallback((error, source) -> {
                Log.e("AsisTechJ2", "Error de cámara: " + error);
                mainHandler.post(() -> {
                    closeCamera();
                    stopScan("La cámara dejó de responder. Vuelve a iniciar el escaneo.");
                });
            });
            camera.setPreviewCallbackWithBuffer((data, source) -> captureFrame(data, source));
            int bufferSize = previewWidth * previewHeight
                    * ImageFormat.getBitsPerPixel(ImageFormat.NV21) / 8;
            camera.addCallbackBuffer(new byte[bufferSize]);
            camera.addCallbackBuffer(new byte[bufferSize]);
            camera.addCallbackBuffer(new byte[bufferSize]);
            camera.startPreview();
            lastPreviewFrameAt = SystemClock.elapsedRealtime();
            mainHandler.removeCallbacks(previewWatchdog);
            mainHandler.postDelayed(previewWatchdog, 5000);
            showStatus("Escaneo activo · máximo 10 minutos.");
        } catch (Exception error) {
            Log.e("AsisTechJ2", "No se pudo iniciar la vista previa de la cámara frontal.", error);
            closeCamera();
            stopScan("No se pudo abrir la cámara frontal.");
        }
    }

    private void restartPreview() {
        Camera currentCamera = camera;
        if (currentCamera == null || !active.get()) {
            return;
        }
        try {
            showStatus("Reiniciando la vista previa de la cámara…");
            currentCamera.stopPreview();
            currentCamera.setPreviewDisplay(surfaceHolder);
            currentCamera.startPreview();
            lastPreviewFrameAt = SystemClock.elapsedRealtime();
            mainHandler.postDelayed(previewWatchdog, 5000);
        } catch (IOException | RuntimeException error) {
            Log.e("AsisTechJ2", "No se pudo reiniciar la vista previa.", error);
            stopScan("No se pudo reiniciar la cámara. Vuelve a iniciar el escaneo.");
        }
    }

    private int findFrontCamera() {
        Camera.CameraInfo info = new Camera.CameraInfo();
        for (int id = 0; id < Camera.getNumberOfCameras(); id++) {
            Camera.getCameraInfo(id, info);
            if (info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT) {
                return id;
            }
        }
        return -1;
    }

    private Camera.Size selectPreviewSize(Camera.Parameters parameters) {
        Camera.Size best = null;
        double bestScore = Double.MAX_VALUE;
        for (Camera.Size size : parameters.getSupportedPreviewSizes()) {
            double areaPenalty = Math.abs((long) size.width * size.height - 640L * 480L);
            double ratioPenalty = Math.abs((double) size.width / size.height - 4.0 / 3.0) * 100000;
            double score = areaPenalty + ratioPenalty;
            if (score < bestScore) {
                best = size;
                bestScore = score;
            }
        }
        return best;
    }

    private int getDisplayOrientation(Camera.CameraInfo info) {
        int rotation = getWindowManager().getDefaultDisplay().getRotation();
        int degrees = rotation == Surface.ROTATION_90 ? 90
                : rotation == Surface.ROTATION_180 ? 180
                : rotation == Surface.ROTATION_270 ? 270 : 0;
        if (info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT) {
            return (360 - (info.orientation + degrees) % 360) % 360;
        }
        return (info.orientation - degrees + 360) % 360;
    }

    private void captureFrame(byte[] data, Camera source) {
        long now = SystemClock.elapsedRealtime();
        lastPreviewFrameAt = now;
        if (!active.get()) {
            returnPreviewBuffer(source, data);
            return;
        }
        if (previewFrameConfirmed.compareAndSet(false, true)) {
            int averageLuma = averageLuma(data, previewWidth, previewHeight);
            showStatus(averageLuma < 8
                    ? "La cámara entrega una imagen negra. Revisa que el lente esté descubierto."
                    : "Cámara frontal activa · buscando rostros.");
        }
        if (now - lastFrameAt < FRAME_INTERVAL_MS
                || !frameInFlight.compareAndSet(false, true)) {
            returnPreviewBuffer(source, data);
            return;
        }
        lastFrameAt = now;
        byte[] frame = data.clone();
        returnPreviewBuffer(source, data);
        int rotation = activeCameraInfo == null ? 0 : activeCameraInfo.orientation;
        networkExecutor.execute(() -> {
            try {
                sendFrame(frame, previewWidth, previewHeight, rotation);
            } catch (Exception error) {
                showStatus("Escaneo activo · reintentando conexión.");
            } finally {
                frameInFlight.set(false);
            }
        });
    }

    private void returnPreviewBuffer(Camera source, byte[] data) {
        try {
            source.addCallbackBuffer(data);
        } catch (RuntimeException error) {
            Log.w("AsisTechJ2", "No se pudo devolver el buffer de la vista previa.", error);
        }
    }

    private int averageLuma(byte[] frame, int width, int height) {
        int yPlaneSize = width * height;
        long total = 0;
        int samples = 0;
        int step = Math.max(1, yPlaneSize / 1000);
        for (int index = 0; index < yPlaneSize && index < frame.length; index += step) {
            total += frame[index] & 0xff;
            samples++;
        }
        return samples == 0 ? 0 : (int) (total / samples);
    }

    private void sendFrame(byte[] data, int width, int height, int rotation) throws Exception {
        ByteArrayOutputStream jpeg = new ByteArrayOutputStream();
        YuvImage image = new YuvImage(data, ImageFormat.NV21, width, height, null);
        if (!image.compressToJpeg(new Rect(0, 0, width, height), 55, jpeg)) {
            throw new IOException("No se pudo codificar el fotograma.");
        }
        JSONObject payload = new JSONObject();
        payload.put("materia_id", materiaId);
        payload.put("rotacion", rotation);
        payload.put("foto", Base64.encodeToString(jpeg.toByteArray(), Base64.NO_WRAP));
        JSONObject response = postJson("/api/camara/telefono/escanear", payload);
        JSONArray faces = response.optJSONArray("rostros");
        if (faces == null) {
            return;
        }

        JSONObject outsideSchedule = null;
        boolean identified = false;
        boolean verifying = false;
        StringBuilder recognizedCodes = new StringBuilder();
        for (int i = 0; i < faces.length(); i++) {
            JSONObject face = faces.optJSONObject(i);
            if (face == null) {
                continue;
            }
            String state = face.optString("estado");
            if ("fuera_horario".equals(state)) {
                outsideSchedule = face;
                break;
            }
            if ("identificado".equals(state)) {
                identified = true;
                if (recognizedCodes.length() > 0) {
                    recognizedCodes.append(',');
                }
                recognizedCodes.append(face.optString("codigo", face.optString("nombre")));
            } else if ("verificando".equals(state)) {
                verifying = true;
            }
        }
        if (outsideSchedule != null) {
            String code = outsideSchedule.optString(
                    "codigo", outsideSchedule.optString("nombre"));
            reportResult("fuera_horario", "Fuera de horario", "fuera_horario:" + code);
        } else if (identified) {
            reportResult("reconocido", "Asistencia correcta", "reconocido:" + recognizedCodes);
        } else if (!verifying && faces.length() > 0) {
            reportResult("desconocido", "Desconocido", "desconocido");
        } else if (faces.length() == 0) {
            lastResultKey = "";
            mainHandler.post(() -> resultView.setText(""));
        }
    }

    private void reportResult(String type, String message, String key) throws Exception {
        if (key.equals(lastResultKey)) {
            return;
        }
        JSONObject payload = new JSONObject();
        payload.put("tablet_id", tabletId);
        payload.put("evento_id", UUID.randomUUID().toString());
        payload.put("tipo", type);
        payload.put("mensaje", message);
        postJson("/api/camara/tablet/resultado", payload);
        lastResultKey = key;
        mainHandler.post(() -> {
            resultView.setText(message);
            resultView.setTextColor("reconocido".equals(type)
                    ? Color.rgb(0, 107, 60)
                    : Color.rgb(164, 74, 0));
        });
    }

    private JSONObject postJson(String path, JSONObject payload) throws Exception {
        HttpURLConnection connection = null;
        try {
            URL url = new URL(BuildConfig.API_BASE_URL + path);
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(4000);
            connection.setReadTimeout(6000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (java.io.OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }
            int status = connection.getResponseCode();
            java.io.InputStream stream = status >= 200 && status < 300
                    ? connection.getInputStream() : connection.getErrorStream();
            ByteArrayOutputStream responseBytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int read;
            if (stream != null) {
                try (java.io.InputStream input = stream) {
                    while ((read = input.read(buffer)) != -1) {
                        responseBytes.write(buffer, 0, read);
                    }
                }
            }
            if (status < 200 || status >= 300) {
                throw new IOException("El servidor respondió HTTP " + status);
            }
            return new JSONObject(new String(responseBytes.toByteArray(), StandardCharsets.UTF_8));
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private void stopScan(String message) {
        if (!active.getAndSet(false)) {
            showStatus(message);
            return;
        }
        mainHandler.removeCallbacks(scanTimeout);
        mainHandler.removeCallbacks(previewWatchdog);
        closeCamera();
        lastResultKey = "";
        resultView.setText("");
        previewView.setVisibility(View.GONE);
        cameraPlaceholder.setVisibility(View.VISIBLE);
        showStatus(message);
    }

    private void closeCamera() {
        if (camera != null) {
            try {
                camera.setPreviewCallbackWithBuffer(null);
                camera.setErrorCallback(null);
                camera.stopPreview();
                camera.release();
            } catch (RuntimeException error) {
                Log.w("AsisTechJ2", "No se pudo liberar correctamente la cámara.", error);
            } finally {
                camera = null;
                activeCameraInfo = null;
            }
        }
    }

    private void showStatus(String message) {
        mainHandler.post(() -> {
            if (statusView != null) {
                statusView.setText(message);
            }
        });
    }
}
