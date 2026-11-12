package com.upec.asistech.j2camera;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.graphics.YuvImage;
import android.graphics.drawable.GradientDrawable;
import android.hardware.Camera;
import android.net.SSLCertificateSocketFactory;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Base64;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.Socket;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.text.SimpleDateFormat;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

@SuppressWarnings("deprecation")
public final class MainActivity extends Activity implements SurfaceHolder.Callback {
    static {
        System.setProperty("java.net.preferIPv4Stack", "true");
        System.setProperty("java.net.preferIPv6Addresses", "false");
        System.setProperty("http.keepAlive", "false");
    }

    private static final String PREFS = "asistech_j2_camera";
    private static final String TABLET_ID_KEY = "tablet_id";
    private static final String TABLET_ID_PREFIX = "j2-aula-";
    private static final String TABLET_NAME = "Galaxy J2 Aula";
    private static final String KEY_SERVER_URL = "custom_server_url";
    private static final String KEY_CAM_FACING = "cam_facing";
    private static final String ADMIN_PIN = "1234";

    private static final long HEARTBEAT_INTERVAL_MS = 1500;
    private static final long FRAME_INTERVAL_MS = 600;
    private static final int CAMERA_PERMISSION_REQUEST = 41;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService networkExecutor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean heartbeatInFlight = new AtomicBoolean(false);
    private final AtomicBoolean frameInFlight = new AtomicBoolean(false);
    private final AtomicBoolean active = new AtomicBoolean(false); // Inactive until teacher starts scan

    // UI Root
    private FrameLayout rootLayout;

    // 1. Standby View Elements
    private LinearLayout standbyLayout;
    private TextView tvStandbyStatus;
    private TextView tvIpBadge;
    private TextView tvWifiBadge;

    // 2. Camera Preview
    private SurfaceView previewView;
    private SurfaceHolder surfaceHolder;

    // 3. Scan Overlay Elements
    private FrameLayout scanOverlayLayout;
    private View reticleView;
    private LinearLayout bottomCard;
    private GradientDrawable bottomCardDrawable;
    private TextView tvStatusBadge;
    private TextView tvStudentName;
    private TextView tvStudentDetail;
    private TextView tvScanServerStatus;

    private WifiManager.WifiLock wifiLock;
    private Camera camera;
    private Camera.CameraInfo activeCameraInfo;
    private int currentFacing = Camera.CameraInfo.CAMERA_FACING_FRONT;
    private String tabletId;
    private int materiaId = 1;
    private long lastFrameAt;
    private String lastResultKey = "";
    private int previewWidth = 640;
    private int previewHeight = 480;
    private long framesSentCount = 0;
    private boolean surfaceReady = false;
    private String effectiveServerUrl;
    private volatile String cachedIpv4Host;
    private volatile String cachedIpv4Addr;
    private volatile long cachedIpv4At;
    private boolean isShowingSuccess = false;

    private final Runnable heartbeatLoop = new Runnable() {
        @Override
        public void run() {
            sendHeartbeat();
            mainHandler.postDelayed(this, HEARTBEAT_INTERVAL_MS);
        }
    };

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        configureDisplay();
        tabletId = getTabletId();

        SharedPreferences preferences = getSharedPreferences(PREFS, MODE_PRIVATE);
        String defaultUrl = BuildConfig.API_BASE_URL;
        String savedUrl = preferences.getString(KEY_SERVER_URL, null);
        if (savedUrl == null || savedUrl.isEmpty()
                || savedUrl.contains("192.168.")
                || savedUrl.contains("172.20.")
                || savedUrl.contains("10.0.")
                || savedUrl.contains("localhost")) {
            effectiveServerUrl = defaultUrl;
            preferences.edit().putString(KEY_SERVER_URL, effectiveServerUrl).apply();
        } else {
            effectiveServerUrl = savedUrl;
        }
        currentFacing = preferences.getInt(KEY_CAM_FACING, Camera.CameraInfo.CAMERA_FACING_FRONT);

        buildScreen();

        try {
            startLockTask();
        } catch (Throwable ignored) {
        }

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

        checkCameraPermissions();
    }

    private void configureDisplay() {
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
        window.clearFlags(WindowManager.LayoutParams.FLAG_FORCE_NOT_FULLSCREEN);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(Color.TRANSPARENT);
            window.setNavigationBarColor(Color.BLACK);
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        WindowManager.LayoutParams attributes = window.getAttributes();
        attributes.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
        window.setAttributes(attributes);
        hideSystemUI();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemUI();
        }
    }

    private void hideSystemUI() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }

    private void buildScreen() {
        rootLayout = new FrameLayout(this);
        rootLayout.setBackgroundColor(Color.WHITE);

        // ==========================================
        // LAYER 0: CAMERA PREVIEW (SurfaceView)
        // ==========================================
        previewView = new SurfaceView(this);
        previewView.setZOrderMediaOverlay(true);
        surfaceHolder = previewView.getHolder();
        surfaceHolder.setType(SurfaceHolder.SURFACE_TYPE_PUSH_BUFFERS);
        surfaceHolder.addCallback(this);
        previewView.setVisibility(View.GONE); // Hidden until teacher commands "iniciar"
        FrameLayout.LayoutParams camParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT);
        rootLayout.addView(previewView, camParams);

        // ==========================================
        // LAYER 1: SCAN OVERLAY (Shown during active camera scan)
        // ==========================================
        scanOverlayLayout = new FrameLayout(this);
        scanOverlayLayout.setVisibility(View.GONE);

        // Vignettes for high contrast
        View topVignette = new View(this);
        GradientDrawable topGrad = new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.argb(190, 0, 0, 0), Color.TRANSPARENT});
        topVignette.setBackground(topGrad);
        FrameLayout.LayoutParams topVignetteParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, dp(110));
        topVignetteParams.gravity = Gravity.TOP;
        scanOverlayLayout.addView(topVignette, topVignetteParams);

        View bottomVignette = new View(this);
        GradientDrawable bottomGrad = new GradientDrawable(
                GradientDrawable.Orientation.BOTTOM_TOP,
                new int[]{Color.argb(230, 0, 0, 0), Color.TRANSPARENT});
        bottomVignette.setBackground(bottomGrad);
        FrameLayout.LayoutParams bottomVignetteParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, dp(260));
        bottomVignetteParams.gravity = Gravity.BOTTOM;
        scanOverlayLayout.addView(bottomVignette, bottomVignetteParams);

        // Active scan top bar
        LinearLayout scanTopBar = new LinearLayout(this);
        scanTopBar.setOrientation(LinearLayout.VERTICAL);
        scanTopBar.setPadding(dp(16), dp(14), dp(16), dp(8));

        TextView tvScanTitle = new TextView(this);
        tvScanTitle.setText("ASISTECH · TERMINAL v" + BuildConfig.VERSION_NAME);
        tvScanTitle.setTextColor(Color.WHITE);
        tvScanTitle.setTextSize(17);
        tvScanTitle.setTypeface(null, android.graphics.Typeface.BOLD);
        tvScanTitle.setGravity(Gravity.CENTER);
        scanTopBar.addView(tvScanTitle);

        tvScanServerStatus = new TextView(this);
        tvScanServerStatus.setText("● Escaneo en vivo · Cámara activa");
        tvScanServerStatus.setTextColor(Color.rgb(0, 230, 118));
        tvScanServerStatus.setTextSize(12);
        tvScanServerStatus.setGravity(Gravity.CENTER);
        scanTopBar.addView(tvScanServerStatus);

        setupAdminTap(scanTopBar);

        FrameLayout.LayoutParams scanTopParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        scanTopParams.gravity = Gravity.TOP;
        scanOverlayLayout.addView(scanTopBar, scanTopParams);

        // Center Biometric Reticle (Amplio para escaneo a distancia natural ~1m a 1.5m)
        reticleView = new View(this);
        GradientDrawable reticleDrawable = new GradientDrawable();
        reticleDrawable.setShape(GradientDrawable.RECTANGLE);
        reticleDrawable.setCornerRadius(dp(36));
        reticleDrawable.setColor(Color.TRANSPARENT);
        reticleDrawable.setStroke(dp(4), Color.rgb(255, 60, 60));
        reticleView.setBackground(reticleDrawable);
        reticleView.setVisibility(View.INVISIBLE);

        FrameLayout.LayoutParams reticleParams = new FrameLayout.LayoutParams(dp(300), dp(380));
        reticleParams.gravity = Gravity.CENTER;
        reticleParams.setMargins(0, dp(-25), 0, 0);
        scanOverlayLayout.addView(reticleView, reticleParams);

        // Bottom Student Info Card
        bottomCard = new LinearLayout(this);
        bottomCard.setOrientation(LinearLayout.VERTICAL);
        bottomCard.setPadding(dp(18), dp(16), dp(18), dp(16));

        bottomCardDrawable = new GradientDrawable();
        bottomCardDrawable.setShape(GradientDrawable.RECTANGLE);
        bottomCardDrawable.setCornerRadius(dp(20));
        bottomCardDrawable.setColor(Color.argb(225, 12, 24, 18));
        bottomCardDrawable.setStroke(dp(2), Color.argb(160, 0, 230, 118));
        bottomCard.setBackground(bottomCardDrawable);

        tvStatusBadge = new TextView(this);
        tvStatusBadge.setText("ESPERANDO ESTUDIANTE...");
        tvStatusBadge.setTextColor(Color.rgb(0, 230, 118));
        tvStatusBadge.setTextSize(16);
        tvStatusBadge.setTypeface(null, android.graphics.Typeface.BOLD);
        bottomCard.addView(tvStatusBadge);

        tvStudentName = new TextView(this);
        tvStudentName.setText("Acérquese a la cámara para registrar asistencia");
        tvStudentName.setTextColor(Color.WHITE);
        tvStudentName.setTextSize(15);
        tvStudentName.setTypeface(null, android.graphics.Typeface.BOLD);
        tvStudentName.setPadding(0, dp(4), 0, dp(2));
        bottomCard.addView(tvStudentName);

        tvStudentDetail = new TextView(this);
        tvStudentDetail.setText("Terminal de Puerta UPEC • Escaneo Facial Continuo");
        tvStudentDetail.setTextColor(Color.rgb(180, 200, 190));
        tvStudentDetail.setTextSize(12);
        bottomCard.addView(tvStudentDetail);

        FrameLayout.LayoutParams cardParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        cardParams.gravity = Gravity.BOTTOM;
        cardParams.setMargins(dp(14), 0, dp(14), dp(16));
        scanOverlayLayout.addView(bottomCard, cardParams);

        rootLayout.addView(scanOverlayLayout, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        // ==========================================
        // LAYER 2: STANDBY SCREEN (Shown while waiting for teacher order)
        // ==========================================
        standbyLayout = new LinearLayout(this);
        standbyLayout.setOrientation(LinearLayout.VERTICAL);
        standbyLayout.setBackgroundColor(Color.WHITE);
        standbyLayout.setPadding(dp(24), dp(32), dp(24), dp(24));

        TextView tvMainTitle = new TextView(this);
        tvMainTitle.setText("ASISTECH · CÁMARA v" + BuildConfig.VERSION_NAME);
        tvMainTitle.setTextColor(Color.rgb(0, 107, 60));
        tvMainTitle.setTextSize(22);
        tvMainTitle.setTypeface(null, android.graphics.Typeface.BOLD);
        tvMainTitle.setGravity(Gravity.CENTER);
        standbyLayout.addView(tvMainTitle);

        setupAdminTap(tvMainTitle);

        tvStandbyStatus = new TextView(this);
        tvStandbyStatus.setText("Conectando con el servidor...");
        tvStandbyStatus.setTextColor(Color.rgb(80, 95, 88));
        tvStandbyStatus.setTextSize(15);
        tvStandbyStatus.setGravity(Gravity.CENTER);
        tvStandbyStatus.setPadding(0, dp(8), 0, dp(16));
        standbyLayout.addView(tvStandbyStatus);

        // Center Placeholder message
        LinearLayout centerHolder = new LinearLayout(this);
        centerHolder.setOrientation(LinearLayout.VERTICAL);
        centerHolder.setGravity(Gravity.CENTER);

        TextView tvCenterMsg = new TextView(this);
        tvCenterMsg.setText("La cámara se activará al iniciar el escaneo.");
        tvCenterMsg.setTextColor(Color.rgb(120, 130, 125));
        tvCenterMsg.setTextSize(16);
        tvCenterMsg.setGravity(Gravity.CENTER);
        centerHolder.addView(tvCenterMsg);

        standbyLayout.addView(centerHolder, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        // Interactive Server IP Pill
        tvIpBadge = new TextView(this);
        tvIpBadge.setText("🌐 Servidor: " + effectiveServerUrl + "\n(Toca aquí para cambiar IP)");
        tvIpBadge.setTextColor(Color.rgb(0, 110, 60));
        tvIpBadge.setTextSize(13);
        tvIpBadge.setTypeface(null, android.graphics.Typeface.BOLD);
        tvIpBadge.setGravity(Gravity.CENTER);
        tvIpBadge.setPadding(dp(16), dp(8), dp(16), dp(8));

        GradientDrawable ipPill = new GradientDrawable();
        ipPill.setShape(GradientDrawable.RECTANGLE);
        ipPill.setCornerRadius(dp(20));
        ipPill.setColor(Color.rgb(232, 246, 238));
        ipPill.setStroke(dp(1), Color.rgb(150, 215, 175));
        tvIpBadge.setBackground(ipPill);
        tvIpBadge.setOnClickListener(v -> showServerConfigDialog());

        LinearLayout.LayoutParams ipParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        ipParams.gravity = Gravity.CENTER_HORIZONTAL;
        ipParams.setMargins(0, 0, 0, dp(10));
        standbyLayout.addView(tvIpBadge, ipParams);

        // Bottom Wi-Fi Pill
        tvWifiBadge = new TextView(this);
        tvWifiBadge.setText("Conectado a red Wi-Fi " + getWifiSsid());
        tvWifiBadge.setTextColor(Color.rgb(70, 180, 240));
        tvWifiBadge.setTextSize(14);
        tvWifiBadge.setTypeface(null, android.graphics.Typeface.BOLD);
        tvWifiBadge.setGravity(Gravity.CENTER);
        tvWifiBadge.setPadding(dp(16), dp(10), dp(16), dp(10));

        GradientDrawable pill = new GradientDrawable();
        pill.setShape(GradientDrawable.RECTANGLE);
        pill.setCornerRadius(dp(24));
        pill.setColor(Color.rgb(65, 75, 70));
        tvWifiBadge.setBackground(pill);

        LinearLayout.LayoutParams pillParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        pillParams.gravity = Gravity.CENTER_HORIZONTAL;
        pillParams.setMargins(0, 0, 0, dp(14));
        standbyLayout.addView(tvWifiBadge, pillParams);

        TextView tvFooter = new TextView(this);
        tvFooter.setText("Cámara frontal · Se detiene automáticamente en 10 minutos");
        tvFooter.setTextColor(Color.GRAY);
        tvFooter.setTextSize(12);
        tvFooter.setGravity(Gravity.CENTER);
        standbyLayout.addView(tvFooter);

        rootLayout.addView(standbyLayout, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        setContentView(rootLayout);
    }

    private void setupAdminTap(View view) {
        final int[] tapCount = {0};
        final long[] lastTapTime = {0};
        view.setOnClickListener(v -> {
            long now = System.currentTimeMillis();
            if (now - lastTapTime[0] < 500) {
                tapCount[0]++;
                if (tapCount[0] >= 5) {
                    tapCount[0] = 0;
                    showAdminDialog();
                }
            } else {
                tapCount[0] = 1;
            }
            lastTapTime[0] = now;
        });
    }

    private String getWifiSsid() {
        try {
            WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null && wm.getConnectionInfo() != null) {
                String ssid = wm.getConnectionInfo().getSSID();
                if (ssid != null && !ssid.isEmpty() && !ssid.equals("<unknown ssid>")) {
                    return ssid.replace("\"", "");
                }
            }
        } catch (Throwable ignored) {
        }
        return "POLITECNICA";
    }

    private void setReticleStyle(int strokeColor, boolean visible) {
        if (!visible) {
            reticleView.setVisibility(View.INVISIBLE);
            return;
        }
        reticleView.setVisibility(View.VISIBLE);
        GradientDrawable ret = new GradientDrawable();
        ret.setShape(GradientDrawable.RECTANGLE);
        ret.setCornerRadius(dp(36));
        ret.setColor(Color.TRANSPARENT);
        ret.setStroke(dp(4), strokeColor);
        reticleView.setBackground(ret);
    }

    private void showSuccessUI(String nombre, String codigo, String estadoAsistencia) {
        isShowingSuccess = true;
        setReticleStyle(Color.rgb(0, 230, 118), true); // Green reticle

        bottomCardDrawable.setColor(Color.argb(245, 4, 46, 22));
        bottomCardDrawable.setStroke(dp(3), Color.rgb(0, 230, 118));
        bottomCard.setBackground(bottomCardDrawable);

        tvStatusBadge.setText("✓ ¡ASISTENCIA TOMADA!");
        tvStatusBadge.setTextColor(Color.rgb(0, 230, 118));

        tvStudentName.setText(nombre.toUpperCase());
        tvStudentName.setTextSize(17);

        SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss", Locale.getDefault());
        String hora = sdf.format(new Date());
        tvStudentDetail.setText("Código: " + codigo + " • Estado: " + estadoAsistencia + " • Hora: " + hora);

        mainHandler.postDelayed(() -> {
            isShowingSuccess = false;
            resetWaitingUI();
        }, 3500);
    }

    private void showVerifyingUI() {
        showVerifyingUI("", 0, 1, 1);
    }

    private void showVerifyingUI(String nombre, int confPercent, int cur, int req) {
        if (isShowingSuccess) return;
        setReticleStyle(Color.rgb(255, 140, 0), true); // Amber reticle during verification

        bottomCardDrawable.setColor(Color.argb(240, 36, 22, 10));
        bottomCardDrawable.setStroke(dp(2), Color.rgb(255, 140, 0));
        bottomCard.setBackground(bottomCardDrawable);

        String badge = (req > 1) ? ("🔍 VALIDANDO IDENTIDAD (" + cur + "/" + req + ")") : "🔍 VALIDANDO IDENTIDAD...";
        tvStatusBadge.setText(badge);
        tvStatusBadge.setTextColor(Color.rgb(255, 170, 50));

        if (nombre != null && !nombre.isEmpty()) {
            tvStudentName.setText(nombre.toUpperCase());
            tvStudentName.setTextSize(17);
            tvStudentDetail.setText("Coincidencia: " + confPercent + "% · Mantenga la vista al frente...");
        } else {
            tvStudentName.setText("Rostro detectado · Analizando...");
            tvStudentName.setTextSize(15);
            tvStudentDetail.setText("Mantenga el rostro quieto frente a la cámara");
        }
    }

    private void showOutsideScheduleUI(String nombre, String mensaje) {
        if (isShowingSuccess) return;
        setReticleStyle(Color.rgb(255, 180, 0), true);

        bottomCardDrawable.setColor(Color.argb(240, 42, 28, 8));
        bottomCardDrawable.setStroke(dp(2), Color.rgb(255, 180, 0));
        bottomCard.setBackground(bottomCardDrawable);

        tvStatusBadge.setText("⚠ FUERA DE HORARIO");
        tvStatusBadge.setTextColor(Color.rgb(255, 180, 0));
        tvStudentName.setText(nombre.toUpperCase());
        tvStudentName.setTextSize(16);
        tvStudentDetail.setText(mensaje);
    }

    private void showUnrecognizedUI() {
        if (isShowingSuccess) return;
        setReticleStyle(Color.rgb(255, 60, 60), true);

        bottomCardDrawable.setColor(Color.argb(235, 48, 14, 14));
        bottomCardDrawable.setStroke(dp(2), Color.rgb(255, 60, 60));
        bottomCard.setBackground(bottomCardDrawable);

        tvStatusBadge.setText("⚠ ROSTRO NO REGISTRADO");
        tvStatusBadge.setTextColor(Color.rgb(255, 82, 82));
        tvStudentName.setText("Rostro no coincide con estudiantes inscritos");
        tvStudentName.setTextSize(15);
        tvStudentDetail.setText("Mire de frente y asegúrese de tener buena iluminación");
    }

    private void resetWaitingUI() {
        if (isShowingSuccess) return;
        setReticleStyle(Color.TRANSPARENT, false);

        bottomCardDrawable.setColor(Color.argb(225, 12, 24, 18));
        bottomCardDrawable.setStroke(dp(2), Color.argb(160, 0, 230, 118));
        bottomCard.setBackground(bottomCardDrawable);

        tvStatusBadge.setText("ESPERANDO ESTUDIANTE...");
        tvStatusBadge.setTextColor(Color.rgb(0, 230, 118));
        tvStudentName.setText("Acérquese a la cámara para registrar asistencia");
        tvStudentName.setTextSize(15);
        tvStudentDetail.setText("Terminal de Puerta UPEC • Escaneo Facial Continuo");
    }

    @Override
    public void onBackPressed() {
        Toast.makeText(this, "Terminal bloqueado. Toque el título 5 veces con PIN para salir.", Toast.LENGTH_SHORT).show();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN || keyCode == KeyEvent.KEYCODE_VOLUME_UP) {
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    private void showAdminDialog() {
        final EditText input = new EditText(this);
        input.setHint("PIN de administrador (1234)");
        input.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD);

        new AlertDialog.Builder(this)
                .setTitle("Acceso Administrador")
                .setMessage("Ingrese PIN de seguridad:")
                .setView(input)
                .setPositiveButton("Desbloquear", (dialog, which) -> {
                    if (ADMIN_PIN.equals(input.getText().toString().trim())) {
                        showServerConfigDialog();
                    } else {
                        Toast.makeText(MainActivity.this, "PIN incorrecto", Toast.LENGTH_SHORT).show();
                        hideSystemUI();
                    }
                })
                .setNegativeButton("Cancelar", (dialog, which) -> hideSystemUI())
                .show();
    }

    private void showServerConfigDialog() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(20), dp(10), dp(20), dp(10));

        TextView lbl = new TextView(this);
        lbl.setText("URL del Servidor Backend:");
        layout.addView(lbl);

        final EditText etUrl = new EditText(this);
        etUrl.setText(effectiveServerUrl);
        layout.addView(etUrl);

        new AlertDialog.Builder(this)
                .setTitle("Ajustes del Terminal")
                .setView(layout)
                .setPositiveButton("Guardar", (d, w) -> {
                    String newUrl = etUrl.getText().toString().trim();
                    if (!newUrl.isEmpty()) {
                        effectiveServerUrl = newUrl;
                        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                                .putString(KEY_SERVER_URL, newUrl).apply();
                        if (tvIpBadge != null) {
                            tvIpBadge.setText("🌐 Servidor: " + effectiveServerUrl + "\n(Toca aquí para cambiar IP)");
                        }
                        Toast.makeText(MainActivity.this, "Servidor guardado: " + newUrl, Toast.LENGTH_SHORT).show();
                    }
                    hideSystemUI();
                })
                .setNeutralButton("Cambiar Cámara", (d, w) -> {
                    currentFacing = (currentFacing == Camera.CameraInfo.CAMERA_FACING_FRONT)
                            ? Camera.CameraInfo.CAMERA_FACING_BACK
                            : Camera.CameraInfo.CAMERA_FACING_FRONT;
                    getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                            .putInt(KEY_CAM_FACING, currentFacing).apply();
                    if (active.get()) {
                        closeCamera();
                        openCamera(currentFacing);
                    }
                    hideSystemUI();
                })
                .setNegativeButton("Salir de App", (d, w) -> {
                    try {
                        stopLockTask();
                    } catch (Throwable ignored) {
                    }
                    finish();
                })
                .show();
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

    private void checkCameraPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        acquireWifiLock();
        hideSystemUI();
        if (active.get() && surfaceReady && camera == null) {
            openCamera(currentFacing);
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

    private void acquireWifiLock() {
        if (wifiLock != null && !wifiLock.isHeld()) {
            wifiLock.acquire();
        }
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        surfaceReady = true;
        if (active.get() && camera == null) {
            openCamera(currentFacing);
        }
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        if (camera != null) {
            try {
                camera.setPreviewDisplay(holder);
                camera.setPreviewCallback((data, cam) -> captureFrame(data, cam));
                camera.startPreview();
            } catch (Throwable error) {
                Log.e("AsisTechJ2", "Error en surfaceChanged: " + error.getMessage());
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
                } else if (response.optString("status").equals("ok")) {
                    mainHandler.post(() -> {
                        if (!active.get()) {
                            tvStandbyStatus.setText("● Conectado a Servidor · Listo para orden docente");
                            tvStandbyStatus.setTextColor(Color.rgb(0, 140, 70));
                        } else if (!isShowingSuccess && framesSentCount == 0) {
                            tvScanServerStatus.setText("● Escaneo en vivo · Cámara activa");
                            tvScanServerStatus.setTextColor(Color.rgb(0, 230, 118));
                        }
                    });
                }
            } catch (Throwable error) {
                final String detail = error.getClass().getSimpleName()
                        + (error.getMessage() != null ? ": " + error.getMessage() : "");
                mainHandler.post(() -> {
                    if (!active.get()) {
                        tvStandbyStatus.setText("○ Sin conexión (" + detail + ") · " + effectiveServerUrl);
                        tvStandbyStatus.setTextColor(Color.rgb(220, 80, 0));
                    } else {
                        tvScanServerStatus.setText("○ Reintentando conexión (" + detail + ")");
                        tvScanServerStatus.setTextColor(Color.rgb(255, 140, 0));
                    }
                });
            } finally {
                heartbeatInFlight.set(false);
            }
        });
    }

    private void handleCommand(JSONObject command) {
        String action = command.optString("action");
        if ("iniciar".equals(action)) {
            materiaId = command.optInt("materia_id", 1);
            if (active.compareAndSet(false, true)) {
                mainHandler.post(this::startScanMode);
            }
        } else if ("detener".equals(action)) {
            if (active.compareAndSet(true, false)) {
                mainHandler.post(this::stopScanMode);
            }
        }
    }

    private void startScanMode() {
        standbyLayout.setVisibility(View.GONE);
        rootLayout.setBackgroundColor(Color.TRANSPARENT);
        previewView.setVisibility(View.VISIBLE);
        scanOverlayLayout.setVisibility(View.VISIBLE);
        resetWaitingUI();
        if (surfaceReady && camera == null) {
            openCamera(currentFacing);
        }
    }

    private void stopScanMode() {
        closeCamera();
        scanOverlayLayout.setVisibility(View.GONE);
        previewView.setVisibility(View.GONE);
        rootLayout.setBackgroundColor(Color.WHITE);
        standbyLayout.setVisibility(View.VISIBLE);
        tvStandbyStatus.setText("● Conectado a Servidor · Listo para orden docente");
        tvStandbyStatus.setTextColor(Color.rgb(0, 140, 70));
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != CAMERA_PERMISSION_REQUEST) {
            return;
        }
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            if (active.get() && surfaceReady && camera == null) {
                openCamera(currentFacing);
            }
        } else {
            Toast.makeText(this, "Se requiere permiso de cámara para el terminal.", Toast.LENGTH_LONG).show();
        }
    }

    private void openCamera(int desiredFacing) {
        if (camera != null || !surfaceReady) {
            return;
        }
        try {
            int cameraId = findCameraByFacing(desiredFacing);
            if (cameraId < 0) {
                cameraId = 0;
            }
            activeCameraInfo = new Camera.CameraInfo();
            Camera.getCameraInfo(cameraId, activeCameraInfo);
            camera = Camera.open(cameraId);

            Camera.Parameters parameters = camera.getParameters();
            Camera.Size previewSize = selectPreviewSize(parameters);
            if (previewSize != null) {
                parameters.setPreviewSize(previewSize.width, previewSize.height);
                previewWidth = previewSize.width;
                previewHeight = previewSize.height;
            }

            try {
                List<String> focusModes = parameters.getSupportedFocusModes();
                if (focusModes != null) {
                    if (focusModes.contains(Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO)) {
                        parameters.setFocusMode(Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO);
                    } else if (focusModes.contains(Camera.Parameters.FOCUS_MODE_AUTO)) {
                        parameters.setFocusMode(Camera.Parameters.FOCUS_MODE_AUTO);
                    }
                }
            } catch (Throwable ignored) {
            }

            parameters.setPreviewFormat(ImageFormat.NV21);
            camera.setParameters(parameters);
            camera.setDisplayOrientation(getDisplayOrientation(activeCameraInfo));
            camera.setPreviewDisplay(surfaceHolder);

            // Continuous preview frames with standard callback (guaranteed on Galaxy J2)
            camera.setPreviewCallback((data, cam) -> captureFrame(data, cam));
            camera.startPreview();

            try {
                Camera.Size actualSize = camera.getParameters().getPreviewSize();
                if (actualSize != null) {
                    previewWidth = actualSize.width;
                    previewHeight = actualSize.height;
                }
            } catch (Throwable ignored) {
            }

            mainHandler.post(this::resetWaitingUI);
        } catch (Throwable error) {
            Log.e("AsisTechJ2", "Error al abrir cámara: " + error.getMessage(), error);
            final String errText = "❌ Error cámara: " + error.getMessage();
            mainHandler.post(() -> {
                tvScanServerStatus.setText(errText);
                tvScanServerStatus.setTextColor(Color.rgb(255, 80, 80));
            });
            closeCamera();
        }
    }

    private int findCameraByFacing(int facing) {
        Camera.CameraInfo info = new Camera.CameraInfo();
        for (int id = 0; id < Camera.getNumberOfCameras(); id++) {
            Camera.getCameraInfo(id, info);
            if (info.facing == facing) {
                return id;
            }
        }
        return -1;
    }

    private Camera.Size selectPreviewSize(Camera.Parameters parameters) {
        Camera.Size best = null;
        double bestScore = Double.MAX_VALUE;
        List<Camera.Size> supported = parameters.getSupportedPreviewSizes();
        if (supported == null || supported.isEmpty()) {
            return null;
        }
        for (Camera.Size size : supported) {
            double areaPenalty = Math.abs((long) size.width * size.height - 640L * 480L);
            double ratioPenalty = Math.abs((double) size.width / size.height - 4.0 / 3.0) * 100000;
            double score = areaPenalty + ratioPenalty;
            if (score < bestScore) {
                best = size;
                bestScore = score;
            }
        }
        return best != null ? best : supported.get(0);
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

    private int getSensorRotation(Camera.CameraInfo info) {
        int rotation = getWindowManager().getDefaultDisplay().getRotation();
        int degrees = rotation == Surface.ROTATION_90 ? 90
                : rotation == Surface.ROTATION_180 ? 180
                : rotation == Surface.ROTATION_270 ? 270 : 0;
        if (info.facing == Camera.CameraInfo.CAMERA_FACING_FRONT) {
            return (info.orientation + degrees) % 360;
        }
        return (info.orientation - degrees + 360) % 360;
    }

    private void captureFrame(byte[] data, Camera source) {
        if (data == null || !active.get() || isShowingSuccess) {
            return;
        }
        long now = SystemClock.elapsedRealtime();
        if (now - lastFrameAt < FRAME_INTERVAL_MS || !frameInFlight.compareAndSet(false, true)) {
            return;
        }
        lastFrameAt = now;
        byte[] frame = data.clone();

        int rotation = (activeCameraInfo != null) ? getSensorRotation(activeCameraInfo) : 270;

        framesSentCount++;
        mainHandler.post(() -> {
            if (!isShowingSuccess) {
                tvScanServerStatus.setText("● Escaneando · " + framesSentCount + " fotogramas");
                tvScanServerStatus.setTextColor(Color.rgb(0, 230, 118));
            }
        });
        networkExecutor.execute(() -> {
            try {
                sendFrame(frame, previewWidth, previewHeight, rotation);
            } catch (Throwable error) {
                Log.w("AsisTechJ2", "Error al enviar fotograma: " + error.getMessage());
                mainHandler.post(() -> {
                    tvScanServerStatus.setText("⚠ Red (" + framesSentCount + "): " + error.getMessage());
                    tvScanServerStatus.setTextColor(Color.rgb(255, 140, 0));
                });
            } finally {
                frameInFlight.set(false);
            }
        });
    }

    private void sendFrame(byte[] data, int width, int height, int rotation) throws Exception {
        ByteArrayOutputStream jpeg = new ByteArrayOutputStream();
        YuvImage image = new YuvImage(data, ImageFormat.NV21, width, height, null);
        if (!image.compressToJpeg(new Rect(0, 0, width, height), 80, jpeg)) {
            throw new IOException("No se pudo codificar el fotograma a JPEG.");
        }
        JSONObject payload = new JSONObject();
        payload.put("materia_id", materiaId);
        payload.put("rotacion", rotation);
        payload.put("foto", Base64.encodeToString(jpeg.toByteArray(), Base64.NO_WRAP));

        JSONObject response = postJson("/api/camara/telefono/escanear", payload);
        JSONArray faces = response.optJSONArray("rostros");
        if (faces == null || faces.length() == 0) {
            lastResultKey = "";
            mainHandler.post(() -> {
                resetWaitingUI();
                tvScanServerStatus.setText("● En vivo · " + framesSentCount + " fotogramas analizados");
                tvScanServerStatus.setTextColor(Color.rgb(0, 230, 118));
            });
            return;
        }

        JSONObject outsideSchedule = null;
        JSONObject identifiedStudent = null;
        JSONObject verifyingFace = null;
        boolean hasUnrecognized = false;

        for (int i = 0; i < faces.length(); i++) {
            JSONObject face = faces.optJSONObject(i);
            if (face == null) continue;
            String state = face.optString("estado");
            if ("fuera_horario".equals(state)) {
                outsideSchedule = face;
                break;
            }
            if ("identificado".equals(state)) {
                identifiedStudent = face;
                break;
            }
            if ("verificando".equals(state)) {
                verifyingFace = face;
            }
            if ("desconocido".equals(state)) {
                hasUnrecognized = true;
            }
        }

        if (outsideSchedule != null) {
            String name = outsideSchedule.optString("nombre", "Estudiante");
            String msg = outsideSchedule.optString("mensaje", "Fuera del horario de clase");
            mainHandler.post(() -> {
                showOutsideScheduleUI(name, msg);
                tvScanServerStatus.setText("⚠ " + msg + ": " + name);
                tvScanServerStatus.setTextColor(Color.rgb(255, 179, 0));
            });
            reportResult("fuera_horario", "Fuera de horario: " + name, "fh:" + name);
        } else if (identifiedStudent != null) {
            String name = identifiedStudent.optString("nombre", "Estudiante");
            String code = identifiedStudent.optString("codigo", "");
            String state = identifiedStudent.optString("asistencia", "Presente");
            mainHandler.post(() -> {
                showSuccessUI(name, code, state);
                tvScanServerStatus.setText("✓ ¡Identificado con éxito! (" + name + ")");
                tvScanServerStatus.setTextColor(Color.rgb(0, 230, 118));
            });
            reportResult("reconocido", "Asistencia tomada: " + name, "rec:" + code);
        } else if (verifyingFace != null) {
            String name = verifyingFace.optString("nombre", "");
            int conf = verifyingFace.optInt("confianza", 0);
            int cur = verifyingFace.optInt("confirmaciones", 1);
            int req = verifyingFace.optInt("requeridas", 2);
            mainHandler.post(() -> {
                showVerifyingUI(name, conf, cur, req);
                tvScanServerStatus.setText("🔍 Validando a " + (name.isEmpty() ? "estudiante" : name) + " (" + cur + "/" + req + ")");
                tvScanServerStatus.setTextColor(Color.rgb(255, 170, 50));
            });
        } else if (hasUnrecognized) {
            mainHandler.post(() -> {
                showUnrecognizedUI();
                tvScanServerStatus.setText("⚠ Rostro no registrado");
                tvScanServerStatus.setTextColor(Color.rgb(255, 82, 82));
            });
        } else {
            mainHandler.post(this::showVerifyingUI);
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
    }

    private String resolveIpv4(String host) {
        if (host == null || host.isEmpty()) {
            return host;
        }
        if (host.matches("^\\d{1,3}(\\.\\d{1,3}){3}$")) {
            return host;
        }
        long now = SystemClock.elapsedRealtime();
        if (host.equals(cachedIpv4Host) && cachedIpv4Addr != null && (now - cachedIpv4At) < 300_000L) {
            return cachedIpv4Addr;
        }
        String found = null;
        try {
            InetAddress[] addresses = InetAddress.getAllByName(host);
            for (InetAddress addr : addresses) {
                if (addr instanceof Inet4Address) {
                    found = addr.getHostAddress();
                    break;
                }
            }
        } catch (Throwable ignored) {
        }
        if (found == null) {
            found = resolveIpv4ViaDoH(host);
        }
        if (found != null) {
            cachedIpv4Host = host;
            cachedIpv4Addr = found;
            cachedIpv4At = now;
            return found;
        }
        return host;
    }

    private String resolveIpv4ViaDoH(String host) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL("https://8.8.8.8/resolve?name="
                    + URLEncoder.encode(host, "UTF-8") + "&type=A");
            conn = (HttpURLConnection) url.openConnection();
            if (conn instanceof HttpsURLConnection) {
                configureTrustAllSsl((HttpsURLConnection) conn, "dns.google");
            }
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);
            conn.setRequestProperty("Accept", "application/dns-json");
            conn.setRequestProperty("Connection", "close");
            if (conn.getResponseCode() == 200) {
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                byte[] buf = new byte[2048];
                int n;
                try (InputStream in = conn.getInputStream()) {
                    while ((n = in.read(buf)) != -1) {
                        out.write(buf, 0, n);
                    }
                }
                JSONObject json = new JSONObject(new String(out.toByteArray(), StandardCharsets.UTF_8));
                JSONArray answers = json.optJSONArray("Answer");
                if (answers != null) {
                    for (int i = 0; i < answers.length(); i++) {
                        JSONObject ans = answers.optJSONObject(i);
                        if (ans != null && ans.optInt("type") == 1) {
                            String ip = ans.optString("data");
                            if (ip != null && ip.matches("^\\d{1,3}(\\.\\d{1,3}){3}$")) {
                                return ip;
                            }
                        }
                    }
                }
            }
        } catch (Throwable ignored) {
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
        return null;
    }

    private JSONObject postJson(String path, JSONObject payload) throws Exception {
        HttpURLConnection connection = null;
        try {
            URL originalUrl = new URL(effectiveServerUrl + path);
            String originalHost = originalUrl.getHost();
            String targetHost = resolveIpv4(originalHost);
            int port = originalUrl.getPort();
            URL connectUrl = (port != -1)
                    ? new URL(originalUrl.getProtocol(), targetHost, port, originalUrl.getFile())
                    : new URL(originalUrl.getProtocol(), targetHost, originalUrl.getFile());

            connection = (HttpURLConnection) connectUrl.openConnection();
            if (connection instanceof HttpsURLConnection) {
                configureTrustAllSsl((HttpsURLConnection) connection, originalHost);
            }
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(12000);
            connection.setDoOutput(true);
            String hostHeader = (port != -1 && port != 80 && port != 443)
                    ? (originalHost + ":" + port) : originalHost;
            connection.setRequestProperty("Host", hostHeader);
            connection.setRequestProperty("Connection", "close");
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("User-Agent", "AsisTech-J2/1.0");
            connection.setRequestProperty("ngrok-skip-browser-warning", "true");

            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }

            int status = connection.getResponseCode();
            InputStream stream = (status >= 200 && status < 300)
                    ? connection.getInputStream() : connection.getErrorStream();

            ByteArrayOutputStream responseBytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int read;
            if (stream != null) {
                try (InputStream input = stream) {
                    while ((read = input.read(buffer)) != -1) {
                        responseBytes.write(buffer, 0, read);
                    }
                }
            }
            if (status < 200 || status >= 300) {
                throw new IOException("HTTP " + status);
            }
            return new JSONObject(new String(responseBytes.toByteArray(), StandardCharsets.UTF_8));
        } catch (Exception error) {
            cachedIpv4Addr = null;
            throw error;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static void configureTrustAllSsl(HttpsURLConnection conn, final String sniHost) {
        try {
            final SSLCertificateSocketFactory ssf =
                    (SSLCertificateSocketFactory) SSLCertificateSocketFactory.getInsecure(12000, null);
            conn.setSSLSocketFactory(new SSLSocketFactory() {
                private Socket configureSocket(Socket socket) {
                    if (socket instanceof SSLSocket) {
                        SSLSocket ssl = (SSLSocket) socket;
                        try {
                            ssf.setHostname(ssl, sniHost);
                        } catch (Throwable ignored) {
                        }
                        try {
                            ssl.setEnabledProtocols(new String[]{"TLSv1.2", "TLSv1.1", "TLSv1"});
                        } catch (Throwable ignored) {
                        }
                    }
                    return socket;
                }
                @Override
                public String[] getDefaultCipherSuites() {
                    return ssf.getDefaultCipherSuites();
                }
                @Override
                public String[] getSupportedCipherSuites() {
                    return ssf.getSupportedCipherSuites();
                }
                @Override
                public Socket createSocket() throws IOException {
                    return configureSocket(ssf.createSocket());
                }
                @Override
                public Socket createSocket(Socket s, String host, int port, boolean autoClose) throws IOException {
                    return configureSocket(ssf.createSocket(s, sniHost, port, autoClose));
                }
                @Override
                public Socket createSocket(String host, int port) throws IOException {
                    return configureSocket(ssf.createSocket(host, port));
                }
                @Override
                public Socket createSocket(String host, int port, InetAddress localHost, int localPort) throws IOException {
                    return configureSocket(ssf.createSocket(host, port, localHost, localPort));
                }
                @Override
                public Socket createSocket(InetAddress host, int port) throws IOException {
                    return configureSocket(ssf.createSocket(host, port));
                }
                @Override
                public Socket createSocket(InetAddress address, int port, InetAddress localAddress, int localPort) throws IOException {
                    return configureSocket(ssf.createSocket(address, port, localAddress, localPort));
                }
            });
            conn.setHostnameVerifier((hostname, session) -> true);
        } catch (Throwable ignored) {
        }
    }

    private void closeCamera() {
        if (camera != null) {
            try {
                camera.setPreviewCallback(null);
                camera.setErrorCallback(null);
                camera.stopPreview();
                camera.release();
            } catch (Throwable error) {
                Log.w("AsisTechJ2", "Error al cerrar cámara: " + error.getMessage());
            } finally {
                camera = null;
                activeCameraInfo = null;
            }
        }
    }
}
