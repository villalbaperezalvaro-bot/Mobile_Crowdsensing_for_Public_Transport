package com.pruebas_inaoe.sensadomovil;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.sqlite.SQLiteDatabase;
import android.graphics.Color;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.PowerManager;
import android.provider.MediaStore;
import android.util.Log;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;
import android.os.Handler;
public class SensorForegroundService extends Service implements SensorEventListener {
    private static final String TAG = "SensorForegroundService";
    private static final int NOTIFICATION_ID = 123;
    private static final String CHANNEL_ID = "SensorServiceChannel";
    private static final int SAMPLING_RATE_US = 20000; // 50 datos/segundo = 20,000 microsegundos
    // Sensores
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private Sensor gyroscope;
    private float[] currentAccelerometerValues = new float[3];
    private float[] currentGyroscopeValues = new float[3];
    // Localización
    private FusedLocationProviderClient fusedLocationClient;
    private LocationCallback locationCallback;
    private double currentLatitude = 0.0;
    private double currentLongitude = 0.0;
    private double currentAltitude = 0.0;
    private float currentAccuracy = 0.0f;
    private float currentSpeed = 0.0f;
    private float currentBearing = 0.0f;
    private float currentVerticalAccuracy = 0.0f;
    private float currentSpeedAccuracy = 0.0f;
    private float currentBearingAccuracy = 0.0f;

    // Archivos CSV
    private OutputStream gpsOutputStream, acelOutputStream, giroOutputStream;
    private Uri gpsFileUri, acelFileUri, giroFileUri;
    private String rutaCapturada, rutaNombreCapturado, tipoTranspCapturado, numUnidad, estadoPasajero, campaniaNombreCapturada;
    // Base de datos
    private DatabaseHelper dbHelper;
    private long currentSesionId = -1;
    private long timestampInicioGlobalMillis;
    // Control
    private boolean isCollecting = false;
    private boolean useGps = true, useAcel = true, useGiro = true;
    private String campaignUuid;


    private Handler gpsHandler = new Handler();
    private Runnable gpsRunnable;


    @Override
    public void onCreate() {
        super.onCreate();

        createNotificationChannel();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                    NOTIFICATION_ID,
                    createNotification(),
                    android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION |
                            android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            );
        } else {
            startForeground(
                    NOTIFICATION_ID,
                    createNotification()
            );
        }
        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        PowerManager.WakeLock wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "SensadoMovil::WakeLock");
        wakeLock.acquire();


        try {
            dbHelper = new DatabaseHelper(this);
            sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
            fusedLocationClient = LocationServices.getFusedLocationProviderClient(this);

            if (sensorManager != null) {
                accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
                gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);

                if (gyroscope == null) {
                    gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE_UNCALIBRATED);
                    if (gyroscope != null) {
                        Log.i(TAG, "Giroscopio estándar no disponible; usando TYPE_GYROSCOPE_UNCALIBRATED de respaldo.");
                    }
                }

                if (accelerometer == null) {
                    Log.w(TAG, "Acelerómetro no disponible en este dispositivo");
                }
                if (gyroscope == null) {
                    Log.w(TAG, "Giroscopio no disponible en este dispositivo (ni estándar ni uncalibrated)");
                }
            }

            locationCallback = new LocationCallback() {
                @Override
                public void onLocationResult(LocationResult locationResult) {
                    // No hacemos nada si el servicio se detuvo o no hay resultado
                    if (!isCollecting || locationResult == null) return;

                    Location location = locationResult.getLastLocation();
                    if (location != null) {
                        try {
                            // --- DATOS QUE YA TENÍAS ---
                            currentLatitude = location.getLatitude();
                            currentLongitude = location.getLongitude();
                            currentAccuracy = location.getAccuracy();
                            currentAltitude = location.hasAltitude() ? location.getAltitude() : 0.0;

                            // --- INICIO DE LA MODIFICACIÓN: CAPTURAR NUEVOS DATOS ---
                            currentSpeed = location.getSpeed(); // Velocidad en m/s
                            currentBearing = location.getBearing(); // Rumbo en grados (0-360)

                            // Estas precisiones solo están disponibles desde Android 8.0 (API 26)
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                currentVerticalAccuracy = location.getVerticalAccuracyMeters();
                                currentSpeedAccuracy = location.getSpeedAccuracyMetersPerSecond();
                                currentBearingAccuracy = location.getBearingAccuracyDegrees();
                            } else {
                                // En versiones antiguas, asignamos 0.0f ya que no existen
                                currentVerticalAccuracy = 0.0f;
                                currentSpeedAccuracy = 0.0f;
                                currentBearingAccuracy = 0.0f;
                            }
                            // --- FIN DE LA MODIFICACIÓN ---

                        } catch (Exception e) {
                            Log.e(TAG, "Error procesando ubicación", e);
                        }
                    }
                }
            };

        } catch (Exception e) {
            Log.e(TAG, "Error crítico en onCreate del servicio", e);
            stopSelf();
        }
    }
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.getAction() != null) {
            startForeground(NOTIFICATION_ID, createNotification());
            switch (intent.getAction()) {
                case "START_SENSING":
                    // Obtener datos iniciales
                    rutaCapturada = intent.getStringExtra("ruta");
                    rutaNombreCapturado = intent.getStringExtra("rutaNombre");
                    tipoTranspCapturado = intent.getStringExtra("tipoTransporte");
                    numUnidad = intent.getStringExtra("unidad");
                    estadoPasajero = intent.getStringExtra("estadoPasajero");
                    campaignUuid = intent.getStringExtra("campaign_uuid");
                    campaniaNombreCapturada = intent.getStringExtra("campaniaNombre");
                    ArrayList<String> sensors = intent.getStringArrayListExtra("sensors");

                    if (sensors != null) {
                        useGps = sensors.contains("gps");
                        useAcel = sensors.contains("accelerometer");
                        useGiro = sensors.contains("gyroscope");
                    } else {
                        useGps = useAcel = useGiro = true;
                    }

                    Log.i(TAG, "Configuración de sensores: GPS=" + useGps + ", Acel=" + useAcel + ", Giro=" + useGiro);
                    Log.i(TAG, "Campaña UUID recibida: " + campaignUuid);

                    startDataCollection();
                    break;

                case "UPDATE_STATE":
                    estadoPasajero = intent.getStringExtra("estadoPasajero");
                    Log.i(TAG, "Estado actualizado a: " + estadoPasajero);
                    break;

                case "STOP_SENSING":
                    // Obtener datos actualizados (pueden ser diferentes de los iniciales)
                    String rutaActual = intent.getStringExtra("ruta");
                    String rutaNombreActual = intent.getStringExtra("rutaNombre");
                    String unidadActual = intent.getStringExtra("unidad");
                    String tipoTransporteActual = intent.getStringExtra("tipoTransporte");

                    if (rutaActual != null && !"0".equals(rutaActual)) {
                        rutaCapturada = rutaActual;
                    }
                    if (rutaNombreActual != null) {
                        rutaNombreCapturado = rutaNombreActual;
                    }
                    if (unidadActual != null && !unidadActual.isEmpty()) {
                        numUnidad = unidadActual;
                    }
                    if (tipoTransporteActual != null && !"0".equals(tipoTransporteActual)) {
                        tipoTranspCapturado = tipoTransporteActual;
                    }

                    // Detener la colección de datos y guardar todo
                    stopDataCollection();

                    // Terminamos el servicio después de limpiar todo
                    stopSelf();
                    break;
            }
        }
        return START_STICKY;
    }

    private String generateUniqueFileName(String prefix) {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault());
        String timestamp = sdf.format(new Date());
        return prefix + "_" + timestamp + "_" + numUnidad + "_" + System.currentTimeMillis() + ".csv";
    }

    private void startDataCollection() {
        if (isCollecting) return;

        isCollecting = true; // Activar recolección antes de iniciar los archivos y listeners

        // Generar nombres únicos para los archivos e inicializarlos solo si el sensor está habilitado y disponible
        if (useGps) {
            initCsvFile(generateUniqueFileName("gps"), "gps");
        }
        if (useAcel && accelerometer != null) {
            initCsvFile(generateUniqueFileName("acel"), "acel");
        } else if (useAcel) {
            Log.w(TAG, "Se solicitó acelerómetro pero el dispositivo no cuenta con dicho sensor.");
        }

        if (useGiro && gyroscope != null) {
            initCsvFile(generateUniqueFileName("giro"), "giro");
        } else if (useGiro) {
            Log.w(TAG, "Se solicitó giroscopio pero el dispositivo no cuenta con dicho sensor.");
        }

        guardarMetadatosEnBD();

        if (useAcel && accelerometer != null) {
            boolean regAcel = sensorManager.registerListener(this, accelerometer, SAMPLING_RATE_US);
            Log.i(TAG, "Registro de listener Acelerómetro: " + (regAcel ? "Exitoso" : "Fallido"));
        }
        if (useGiro && gyroscope != null) {
            boolean regGiro = sensorManager.registerListener(this, gyroscope, SAMPLING_RATE_US);
            Log.i(TAG, "Registro de listener Giroscopio: " + (regGiro ? "Exitoso" : "Fallido"));
        }

        if (useGps) {
            LocationRequest locationRequest = new LocationRequest.Builder(1000)
                    .setPriority(LocationRequest.PRIORITY_HIGH_ACCURACY)
                    .setMinUpdateIntervalMillis(1000)
                    .build();

            try {
                fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback, null);
            } catch (SecurityException e) {
                Log.e(TAG, "Error de permisos de ubicación: " + e.getMessage());
            }

            // ==== BLOQUE: escritura GPS cada 1 segundo ====
            gpsRunnable = new Runnable() {
                @Override
                public void run() {
                    if (isCollecting && gpsOutputStream != null) {
                        String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.getDefault())
                                .format(new Date());
                        try {
                            String gpsRow = String.format(Locale.US,
                                    "%s,%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%s\n",
                                    timestamp,
                                    currentLatitude,
                                    currentLongitude,
                                    currentAltitude,
                                    currentAccuracy,
                                    currentSpeed,
                                    currentBearing,
                                    currentVerticalAccuracy,
                                    currentSpeedAccuracy,
                                    currentBearingAccuracy,
                                    estadoPasajero
                            );
                            gpsOutputStream.write(gpsRow.getBytes("UTF-8"));
                        }
                        catch (IOException e) {
                            Log.e(TAG, "Error escribiendo datos GPS", e);
                        }

                        // volver a ejecutar en 1 segundo
                        gpsHandler.postDelayed(this, 1000);
                    }
                }
            };
            gpsHandler.postDelayed(gpsRunnable, 1000);
        }

        isCollecting = true;
        Log.i(TAG, "Servicio de sensado iniciado");
    }

    private void stopDataCollection() {
        if (!isCollecting) return;

        sensorManager.unregisterListener(this);
        fusedLocationClient.removeLocationUpdates(locationCallback);

        boolean archivosCreados = true;

        try {
            if (gpsOutputStream != null) {
                gpsOutputStream.flush();
                gpsOutputStream.close();
            } else {
                archivosCreados = false;
            }

            if (acelOutputStream != null) {
                acelOutputStream.flush();
                acelOutputStream.close();
            } else {
                archivosCreados = false;
            }

            if (giroOutputStream != null) {
                giroOutputStream.flush();
                giroOutputStream.close();
            } else {
                archivosCreados = false;
            }
        } catch (IOException e) {
            Log.e(TAG, "Error al cerrar archivos", e);
            archivosCreados = false;
        }

        // Verificar si faltan datos importantes (Ruta, Unidad o Tipo)
        boolean datosCompletos = rutaCapturada != null && !"0".equals(rutaCapturada) && !rutaCapturada.isEmpty() &&
                numUnidad != null && !numUnidad.isEmpty() &&
                tipoTranspCapturado != null && !"0".equals(tipoTranspCapturado) && !tipoTranspCapturado.isEmpty();

        if (currentSesionId != -1) {
            actualizarMetadatosCompletos(); // Nuevo método para actualizar todos los campos
        }

        if (gpsHandler != null && gpsRunnable != null) {
            gpsHandler.removeCallbacks(gpsRunnable);
        }

        isCollecting = false;

        // Enviar broadcast con el resultado
        Intent resultIntent = new Intent("SENSADO_COMPLETADO");
        resultIntent.putExtra("archivos_creados", archivosCreados);
        resultIntent.putExtra("faltan_datos", !datosCompletos);
        resultIntent.putExtra("ruta", rutaCapturada);
        resultIntent.putExtra("unidad", numUnidad);
        resultIntent.putExtra("tipoTransporte", tipoTranspCapturado);
        sendBroadcast(resultIntent);

        Log.i(TAG, "Servicio de sensado detenido. Archivos creados: " + archivosCreados);
    }

    private void actualizarMetadatosCompletos() {
        SQLiteDatabase db = dbHelper.getWritableDatabase();
        ContentValues values = new ContentValues();

        // Actualizar todos los campos importantes
        values.put(MetadatosContract.SesionEntry.COLUMN_ROUTE_NAME, rutaCapturada);
        values.put(MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME, rutaNombreCapturado);
        values.put(MetadatosContract.SesionEntry.COLUMN_TRANSPORT_TYPE, tipoTranspCapturado);
        values.put(MetadatosContract.SesionEntry.COLUMN_UNIT_NUMBER, numUnidad);
        values.put(MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME, campaniaNombreCapturada);
        values.put(MetadatosContract.SesionEntry.COLUMN_END_TIMESTAMP, System.currentTimeMillis());

        try {
            int updatedRows = db.update(
                    MetadatosContract.SesionEntry.TABLE_NAME,
                    values,
                    MetadatosContract.SesionEntry._ID + " = ?",
                    new String[]{String.valueOf(currentSesionId)}
            );

            if (updatedRows > 0) {
                Log.i(TAG, "Metadatos actualizados con valores finales");
            } else {
                Log.w(TAG, "No se actualizaron los metadatos");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error al actualizar metadatos", e);
        } finally {
            db.close();
        }
    }
    private void initCsvFile(String fileName, String type) {
        ContentResolver resolver = getContentResolver();
        ContentValues contentValues = new ContentValues();
        contentValues.put(MediaStore.MediaColumns.DISPLAY_NAME, fileName);
        contentValues.put(MediaStore.MediaColumns.MIME_TYPE, "text/csv");

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                contentValues.put(MediaStore.MediaColumns.RELATIVE_PATH,
                        Environment.DIRECTORY_DOWNLOADS + "/SensadoMovil");
                Uri fileUri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, contentValues);

                if (fileUri != null) {
                    OutputStream outputStream = resolver.openOutputStream(fileUri);
                    if (outputStream != null) {
                        switch (type) {
                            case "gps":
                                gpsFileUri = fileUri;
                                gpsOutputStream = outputStream;
                                outputStream.write(
                                        "Timestamp,Latitud,Longitud,Altitud,Precision,Velocidad,Rumbo,PrecisionVertical,PrecisionVelocidad,PrecisionRumbo,Estado\n"
                                                .getBytes("UTF-8"));
                                break;
                            case "acel":
                                acelFileUri = fileUri;
                                acelOutputStream = outputStream;
                                outputStream.write("Timestamp,AccelX,AccelY,AccelZ,Estado\n".getBytes("UTF-8"));
                                break;
                            case "giro":
                                giroFileUri = fileUri;
                                giroOutputStream = outputStream;
                                outputStream.write("Timestamp,GyroX,GyroY,GyroZ,Estado\n".getBytes("UTF-8"));
                                break;
                        }
                    }
                }
            } else {
                File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                File appDir = new File(downloadsDir, "SensadoMovil");

                if (!appDir.exists() && !appDir.mkdirs()) {
                    Log.e(TAG, "Error creando directorio SensadoMovil");
                    return;
                }

                File file = new File(appDir, fileName);
                OutputStream outputStream = new FileOutputStream(file);

                switch (type) {
                    case "gps":
                        gpsFileUri = Uri.fromFile(file);
                        gpsOutputStream = outputStream;
                        outputStream.write("Timestamp,Latitud,Longitud,Altitud,Precision,Estado\n".getBytes("UTF-8"));
                        break;
                    case "acel":
                        acelFileUri = Uri.fromFile(file);
                        acelOutputStream = outputStream;
                        outputStream.write("Timestamp,AccelX,AccelY,AccelZ,Estado\n".getBytes("UTF-8"));
                        break;
                    case "giro":
                        giroFileUri = Uri.fromFile(file);
                        giroOutputStream = outputStream;
                        outputStream.write("Timestamp,GyroX,GyroY,GyroZ,Estado\n".getBytes("UTF-8"));
                        break;
                }
            }
        } catch (IOException e) {
            Log.e(TAG, "Error inicializando archivo CSV: " + e.getMessage());
        }
    }

    // Método para guardar metadatos
    private void guardarMetadatosEnBD() {
        // Si ya tenemos un ID de sesión, no necesitamos crear uno nuevo
        if (currentSesionId != -1) {
            return;
        }

        SQLiteDatabase db = dbHelper.getWritableDatabase();
        db.beginTransaction();

        try {
            ContentValues values = new ContentValues();
            timestampInicioGlobalMillis = System.currentTimeMillis();

            SharedPreferences prefs = getSharedPreferences("AUTH", MODE_PRIVATE);
            int userId = prefs.getInt("user_id", -1);

            // Generar path_id solo una vez al inicio
            int pathId = dbHelper.getNextPath_id(db);

            // Insertar datos principales
            values.put(MetadatosContract.SesionEntry.COLUMN_PATH_ID, pathId);
            values.put(MetadatosContract.SesionEntry.COLUMN_USER_ID, userId);
            values.put(MetadatosContract.SesionEntry.COLUMN_ROUTE_NAME, rutaCapturada);
            values.put(MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME, rutaNombreCapturado);
            values.put(MetadatosContract.SesionEntry.COLUMN_START_TIMESTAMP, timestampInicioGlobalMillis);
            values.put(MetadatosContract.SesionEntry.COLUMN_TRANSPORT_TYPE, tipoTranspCapturado);
            values.put(MetadatosContract.SesionEntry.COLUMN_UNIT_NUMBER, numUnidad);
            values.put(MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_UUID, campaignUuid);
            values.put(MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME, campaniaNombreCapturada);



            currentSesionId = db.insert(MetadatosContract.SesionEntry.TABLE_NAME, null, values);

            if (currentSesionId != -1) {
                // Guardar referencias de archivos solo para los sensores activos
                if (useGps) saveFileReference(db, gpsFileUri, "gps");
                if (useAcel) saveFileReference(db, acelFileUri, "acel");
                if (useGiro) saveFileReference(db, giroFileUri, "giro");

                db.setTransactionSuccessful();
                Log.i(TAG, "Metadatos guardados correctamente. Sesión ID: " + currentSesionId);
            }
        } finally {
            db.endTransaction();
        }
    }

    // Método para guardar referencia de archivos (sin cambios)
    private void saveFileReference(SQLiteDatabase db, Uri fileUri, String fileType) {
        if (fileUri != null && currentSesionId != -1) {
            try {
                ContentValues fileValues = new ContentValues();
                fileValues.put(MetadatosContract.SessionFileEntry.COLUMN_SESSION_ID_FK, currentSesionId);
                fileValues.put(MetadatosContract.SessionFileEntry.COLUMN_FILE_TYPE, fileType);
                fileValues.put(MetadatosContract.SessionFileEntry.COLUMN_FILE_NAME, fileUri.toString());
                fileValues.put(MetadatosContract.SessionFileEntry.COLUMN_IS_SYNCED, 0);

                db.insert(MetadatosContract.SessionFileEntry.TABLE_NAME, null, fileValues);
            } catch (Exception e) {
                Log.e(TAG, "Error al guardar referencia de archivo " + fileType, e);
            }
        }
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (!isCollecting) return;

        String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.getDefault())
                .format(new Date());

        try {
            switch (event.sensor.getType()) {
                case Sensor.TYPE_ACCELEROMETER:
                    System.arraycopy(event.values, 0, currentAccelerometerValues, 0, event.values.length);
                    if (acelOutputStream != null) {
                        String acelRow = String.format(Locale.US, "%s,%.6f,%.6f,%.6f,%s\n",
                                timestamp,
                                currentAccelerometerValues[0], currentAccelerometerValues[1], currentAccelerometerValues[2],
                                estadoPasajero);
                        acelOutputStream.write(acelRow.getBytes("UTF-8"));
                    }
                    break;

                case Sensor.TYPE_GYROSCOPE:
                case Sensor.TYPE_GYROSCOPE_UNCALIBRATED:
                    System.arraycopy(event.values, 0, currentGyroscopeValues, 0, Math.min(3, event.values.length));
                    if (giroOutputStream != null) {
                        String giroRow = String.format(Locale.US, "%s,%.6f,%.6f,%.6f,%s\n",
                                timestamp,
                                currentGyroscopeValues[0], currentGyroscopeValues[1], currentGyroscopeValues[2],
                                estadoPasajero);
                        giroOutputStream.write(giroRow.getBytes("UTF-8"));
                    }
                    break;
            }


        } catch (IOException e) {
            Log.e(TAG, "Error escribiendo en archivo CSV: " + e.getMessage());
        }
    }
    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // Solo requisito
    }
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // Configurar el patrón de vibración (500ms vibrar, 500ms pausa)
            long[] vibrationPattern = {500, 500};

            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Servicio de Sensado",
                    NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("Recolectando datos de sensores");
            channel.enableVibration(true);
            channel.setVibrationPattern(vibrationPattern);
            channel.setImportance(NotificationManager.IMPORTANCE_HIGH);
            channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);

            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(channel);
        }
    }

    private Notification createNotification() {
        Intent notificationIntent = new Intent(this, FormActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0,
                notificationIntent, PendingIntent.FLAG_IMMUTABLE);

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Sensado en progreso")
                .setContentText("Recolectando datos de sensores")
                .setSmallIcon(R.drawable.ic_notification)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setVibrate(new long[]{500, 500}) // Vibración al aparecer
                .build();
    }


    @Override
    public void onDestroy() {
        super.onDestroy();
        stopDataCollection();
        currentSesionId = -1; // Resetear ID al destruir
        if (dbHelper != null) {
            dbHelper.close();
        }
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}