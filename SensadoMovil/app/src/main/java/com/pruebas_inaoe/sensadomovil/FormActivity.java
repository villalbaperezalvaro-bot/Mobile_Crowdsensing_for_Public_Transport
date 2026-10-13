package com.pruebas_inaoe.sensadomovil;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.ActivityManager;
import android.content.BroadcastReceiver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.sqlite.SQLiteDatabase;
import android.location.LocationManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.provider.Settings;
import android.util.Log;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.AutoCompleteTextView;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;
import java.util.List;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
/**
 * Actividad principal que gestiona el inicio/detención del sensado de transporte.
 * - Controla permisos de ubicación.
 * - Maneja la interfaz de selección de ruta/unidad/estado.
 * - Inicia/detiene el servicio en primer plano.
 */
public class FormActivity extends AppCompatActivity {

    // CONSTANTES PARA SOLICITUDES DE PERMISOS
    private static final int LOCATION_PERMISSION_REQUEST_CODE = 101;
    private static final int BACKGROUND_LOCATION_PERMISSION_REQUEST_CODE = 102;
    private static final int REQUEST_CODE_BATTERY_OPTIMIZATIONS = 1002;
    private static final int REQUEST_CODE_LOCATION_SETTINGS = 1003;
    private static final int REQUEST_CODE_NOTIFICATION_PERMISSION = 1004;
    private static final int REQUEST_CODE_REQUIRED_PERMISSIONS = 1005;
    private static final String TAG = "FormActivity"; // Etiqueta para logs

    // COMPONENTES DE LA INTERFAZ
    private RadioGroup statusRadioGroup; // Grupo de opciones para estado del pasajero
    private AutoCompleteTextView spinnerRuta;        // Selector con búsqueda para ruta
    private AutoCompleteTextView spinnerTipoTransp;  // Selector con búsqueda para tipo de transporte
    private Button btnIniciarSensado;   // Botón para iniciar el sensado
    private Button btnDetenerSensado;   // Botón para detener el sensado
    private Button btnVerArchivos;      // Botón para ver archivos guardados
    private TextView textSensando;      // Texto que indica estado del sensado
    private ProgressBar progressBar;    // Barra de progreso durante el sensado

    // RECEPTOR DE MENSAJES DEL SERVICIO
    private BroadcastReceiver sensadoReceiver;

    // VARIABLES DE ESTADO
    private String currentRuta = "0";       // Ruta actual seleccionada (0 = no seleccionada)
    private String currentUnidad = "0";     // Unidad actual seleccionada
    private String currentTipoTransp = "0"; // Tipo de transporte seleccionado

    // Variable para almacenar el ID de la campaña seleccionada  Agregada aquí  miercoles 24 de octubre
    private String campaignUuidSeleccionado = null;
    private ArrayList<String> selectedSensors = new ArrayList<>();
    private EditText editUnidad;




    // MÉTODO PRINCIPAL - INICIO DE LA ACTIVIDAD
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Configuración inicial
        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO); // Fuerza modo claro
        setContentView(R.layout.activity_form); // Establece el layout

        //

        //

        checkRequiredPermissions(); // Verifica permisos necesarios

        // Recuperar la campaña activa
        SharedPreferences prefsAuth = getSharedPreferences("AUTH", MODE_PRIVATE);
        String campaniaNombre = prefsAuth.getString("campania_activa", "No definida");
        campaignUuidSeleccionado = prefsAuth.getString("campaign_uuid", null);

        Log.d(TAG, "Campaña activa: " + campaniaNombre + " (UUID: " + campaignUuidSeleccionado + ")");
        Toast.makeText(this, "Campaña activa: " + campaniaNombre, Toast.LENGTH_SHORT).show();

        // 1. Identificar vistas primero para que no sean null
        findViews(); 
        
        // 2. Cargar JSON y configurar adaptadores (ahora las vistas ya existen)
        cargarEstadosDesdeJson(); 
        
        // 3. Restaurar datos si hay sensado activo (necesita adaptadores listos)
        boolean isRunning = isServiceRunning(SensorForegroundService.class);
        if (isRunning) {
            restaurarDatosDeSensado();
        }
        updateUIForRunningState(isRunning);

        // 4. Configurar el resto
        setupButtonListeners();

        // Listener para cambios en el estado del pasajero
        statusRadioGroup.setOnCheckedChangeListener((group, checkedId) -> {
            if (isServiceRunning(SensorForegroundService.class)) {
                RadioButton selectedRadio = findViewById(checkedId);
                if (selectedRadio != null) {
                    // Guardar el ID del estado para persistencia
                    int stateId = (int) selectedRadio.getTag();
                    getSharedPreferences("SENSADO", MODE_PRIVATE).edit().putInt("last_state_id", stateId).apply();

                    String newState = getSelectedPassengerState();
                    // Envía actualización al servicio
                    Intent serviceIntent = new Intent(this, SensorForegroundService.class);
                    serviceIntent.setAction("UPDATE_STATE");
                    serviceIntent.putExtra("estadoPasajero", newState);
                    startService(serviceIntent);
                    // Notificación al usuario
                    Toast.makeText(this, "Estado cambiado a: " + selectedRadio.getText(), Toast.LENGTH_SHORT).show();
                }
            }
        });

        // Configuración del BroadcastReceiver para eventos del servicio
        sensadoReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                boolean archivosCreados = intent.getBooleanExtra("archivos_creados", false);
                boolean faltanDatos = intent.getBooleanExtra("faltan_datos", false);

                if (faltanDatos) {
                    String ruta = intent.getStringExtra("ruta");
                    String unidad = intent.getStringExtra("unidad");
                    String tipoTransp = intent.getStringExtra("tipoTransporte");
                    showSimpleDataDialog(ruta, unidad, tipoTransp); // Muestra diálogo para completar datos
                } else if (archivosCreados) {
                    Toast.makeText(FormActivity.this, "Datos guardados correctamente", Toast.LENGTH_SHORT).show();
                }
            }
        };
    }
    /**
     * Muestra un diálogo simple para que el usuario complete los datos del viaje
     * cuando el servicio lo solicita.
     * @param ruta La ruta actual (puede estar vacía).
     * @param unidad La unidad actual (puede estar vacía).
     * @param tipoTransp El tipo de transporte actual (puede estar vacío).
     */
    private void showSimpleDataDialog(String ruta, String unidad, String tipoTransp) {
        // No mostramos el diálogo si ya hay uno visible, para evitar duplicados.
        if (getSupportFragmentManager().findFragmentByTag("SimpleDataDialog") != null) {
            return;
        }

        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Completa la información del viaje");
        builder.setMessage("Por favor, ingresa los datos del vehículo que has abordado.");

        // Usamos el mismo layout que ya creaste para el diálogo de detener.
        View dialogView = getLayoutInflater().inflate(R.layout.dialog_complete_data, null);
        builder.setView(dialogView);

        // Referencias a los componentes del diálogo (Ahora AutoCompleteTextView)
        AutoCompleteTextView dialogSpinnerRuta = dialogView.findViewById(R.id.dialogSpinnerRuta);
        EditText dialogEditUnidad = dialogView.findViewById(R.id.dialogEditUnidad);
        AutoCompleteTextView dialogSpinnerTransporte = dialogView.findViewById(R.id.dialogSpinnerTipoTransp);

        // Configurar adaptadores (Casteo seguro)
        if (spinnerRuta.getAdapter() instanceof ArrayAdapter) {
            dialogSpinnerRuta.setAdapter((ArrayAdapter<String>) spinnerRuta.getAdapter());
        }
        if (spinnerTipoTransp.getAdapter() instanceof ArrayAdapter) {
            dialogSpinnerTransporte.setAdapter((ArrayAdapter<String>) spinnerTipoTransp.getAdapter());
        }

        // Configurar comportamiento de clic para mostrar lista completa
        dialogSpinnerRuta.setOnClickListener(v -> dialogSpinnerRuta.showDropDown());
        dialogSpinnerTransporte.setOnClickListener(v -> dialogSpinnerTransporte.showDropDown());

        // Pre-llenar con datos existentes si el servicio ya tenía algo o se pasaron como argumentos
        if (ruta != null && !ruta.equals("0") && !ruta.isEmpty()) {
            setSelectionByValue(dialogSpinnerRuta, ruta);
        }
        if (unidad != null && !unidad.isEmpty()) {
            dialogEditUnidad.setText(unidad);
        }
        if (tipoTransp != null && !tipoTransp.equals("0") && !tipoTransp.isEmpty()) {
            setSelectionByValue(dialogSpinnerTransporte, tipoTransp);
        }

        builder.setCancelable(false); // No se puede cancelar

        builder.setPositiveButton("Guardar", (dialog, which) -> {
            String nuevaRuta = getNumericIdFromAutoComplete(dialogSpinnerRuta);
            String nuevaUnidad = dialogEditUnidad.getText().toString().trim();
            String nuevoTipoTransp = getNumericIdFromAutoComplete(dialogSpinnerTransporte);

            if (nuevaRuta.equals("0") || nuevaUnidad.isEmpty() || nuevoTipoTransp.equals("0")) {
                Toast.makeText(this, "Debes completar todos los campos", Toast.LENGTH_LONG).show();
                // Si falla la validación, volvemos a mostrar el diálogo.
                showSimpleDataDialog(nuevaRuta, nuevaUnidad, nuevoTipoTransp);
            } else {
                // Datos validados, los guardamos en SharedPreferences para la sincronización
                SharedPreferences prefs = getSharedPreferences("SENSADO", MODE_PRIVATE);
                prefs.edit()
                        .putString("route_id", nuevaRuta)
                        .putString("unit_id", nuevaUnidad)
                        .putString("vehicle_type_id", nuevoTipoTransp)
                        .apply();

                Toast.makeText(this, "Datos del viaje actualizados.", Toast.LENGTH_SHORT).show();
            }
        });

        // Usamos un tag para poder comprobar si el diálogo ya está mostrándose.
        builder.create().show();
    }

    private void findViews() {
        statusRadioGroup = findViewById(R.id.statusRadioGroup);
        spinnerRuta = findViewById(R.id.spinnerRuta);
        editUnidad = findViewById(R.id.editUnidad);
        spinnerTipoTransp = findViewById(R.id.spinnerTipoTransp);
        btnIniciarSensado = findViewById(R.id.btnIniciarSensado);
        btnDetenerSensado = findViewById(R.id.btnDetenerSensado);
        btnVerArchivos = findViewById(R.id.btnVerArchivos);
        textSensando = findViewById(R.id.textSensando);
        progressBar = findViewById(R.id.progressBarSensado);
    }

    private void restaurarDatosDeSensado() {
        SharedPreferences prefs = getSharedPreferences("SENSADO", MODE_PRIVATE);
        String routeId = prefs.getString("route_id", "0");
        String unitId = prefs.getString("unit_id", "");
        String vehicleTypeId = prefs.getString("vehicle_type_id", "0");

        // Intentar encontrar y poner el texto completo en los AutoCompleteTextView
        // Nota: Esto asume que el adaptador ya está cargado. 
        // Si no, tendremos que llamar a esto después de cargar los adaptadores.
        if (!routeId.equals("0")) {
            setSelectionByValue(spinnerRuta, routeId);
        }
        if (!unitId.isEmpty()) {
            editUnidad.setText(unitId);
        }
        if (!vehicleTypeId.equals("0")) {
            setSelectionByValue(spinnerTipoTransp, vehicleTypeId);
        }
    }

    private void setSelectionByValue(AutoCompleteTextView view, String value) {
        if (view.getAdapter() == null) return;
        for (int i = 0; i < view.getAdapter().getCount(); i++) {
            String item = (String) view.getAdapter().getItem(i);
            if (item.startsWith(value + " - ")) {
                view.setText(item, false);
                break;
            }
        }
    }
    // para crear botones radiobuton de estados
    private void cargarEstadosDesdeJson() {

        try {
            SharedPreferences authPrefs = getSharedPreferences("AUTH", MODE_PRIVATE);
            String jsonFileName = authPrefs.getString("config_json_file", "estados.json");

            Log.d(TAG, "Cargando configuración desde assets/" + jsonFileName);

            InputStream is = getAssets().open(jsonFileName);

            int size = is.available();

            byte[] buffer = new byte[size];

            is.read(buffer);

            is.close();

            String json = new String(buffer, "UTF-8");

            JSONObject object = new JSONObject(json);

            JSONObject data = object.getJSONObject("data");

            JSONArray estados = data.getJSONArray("estados");
            JSONArray rutas = data.getJSONArray("routes");
            JSONArray transportes = data.getJSONArray("vehicle_types");
            JSONArray sensores = data.optJSONArray("sensors");

            generarRadioButtons(estados);
            poblarSpinnerDesdeJson(spinnerRuta, rutas, "Seleccione una ruta");
            poblarSpinnerDesdeJson(spinnerTipoTransp, transportes, "Seleccione tipo de transporte");

            selectedSensors.clear();
            if (sensores != null) {
                for (int i = 0; i < sensores.length(); i++) {
                    selectedSensors.add(sensores.getString(i));
                }
            } else {
                // Por defecto, activar todos si no se define
                selectedSensors.add("gps");
                selectedSensors.add("accelerometer");
                selectedSensors.add("gyroscope");
            }

        } catch (Exception e) {

            e.printStackTrace();

        }

    }

    private void poblarSpinnerDesdeJson(AutoCompleteTextView autoComplete, JSONArray jsonArray, String hint) {
        List<String> lista = new ArrayList<>();
        // No añadimos el hint a la lista para no entorpecer la búsqueda
        
        for (int i = 0; i < jsonArray.length(); i++) {
            try {
                JSONObject obj = jsonArray.getJSONObject(i);
                String item = obj.getInt("id") + " - " + obj.getString("name");
                lista.add(item);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_dropdown_item_1line, lista);
        autoComplete.setAdapter(adapter);
        
        // Configurar para mostrar todos los elementos al hacer clic
        autoComplete.setOnClickListener(v -> autoComplete.showDropDown());
        autoComplete.setOnFocusChangeListener((v, hasFocus) -> {
            if (hasFocus) autoComplete.showDropDown();
        });
    }

    private void generarRadioButtons(JSONArray estados) {

        statusRadioGroup.removeAllViews();

        for (int i = 0; i < estados.length(); i++) {

            try {

                JSONObject estado = estados.getJSONObject(i);

                RadioButton rb = new RadioButton(this);
                rb.setId(View.generateViewId());
                rb.setTag(estado.getInt("id"));
                rb.setText(estado.getString("name"));
                rb.setTextSize(16);
                rb.setTextColor(androidx.core.content.ContextCompat.getColor(this, R.color.black));

                // Diseño tipo lista
                rb.setPadding(32, 40, 32, 40);
                rb.setLayoutParams(new RadioGroup.LayoutParams(
                        RadioGroup.LayoutParams.MATCH_PARENT,
                        RadioGroup.LayoutParams.WRAP_CONTENT));

                statusRadioGroup.addView(rb);

                // Añadir divisor si no es el último elemento
                if (i < estados.length() - 1) {
                    View divider = new View(this);
                    RadioGroup.LayoutParams params = new RadioGroup.LayoutParams(
                            RadioGroup.LayoutParams.MATCH_PARENT, 2);
                    params.setMargins(32, 0, 32, 0);
                    divider.setLayoutParams(params);
                    divider.setBackgroundColor(android.graphics.Color.parseColor("#EEEEEE"));
                    statusRadioGroup.addView(divider);
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        // Restaurar selección si hay un sensado activo
        if (isServiceRunning(SensorForegroundService.class)) {
            int lastId = getSharedPreferences("SENSADO", MODE_PRIVATE).getInt("last_state_id", -1);
            if (lastId != -1) {
                for (int i = 0; i < statusRadioGroup.getChildCount(); i++) {
                    View v = statusRadioGroup.getChildAt(i);
                    if (v instanceof RadioButton) {
                        RadioButton rb = (RadioButton) v;
                        if (rb.getTag() != null && (int) rb.getTag() == lastId) {
                            rb.setChecked(true);
                            break;
                        }
                    }
                }
            }
        }
    }




    // CONFIGURACIÓN DE EVENTOS DE BOTONES
    private void setupButtonListeners() {
        // Botón "Iniciar Sensado"
        btnIniciarSensado.setOnClickListener(v -> {
            if (validateFields()) {
                checkPermissionsAndStartService(); // Verifica permisos antes de iniciar
            }
        });

        // Botón "Detener Sensado"
        btnDetenerSensado.setOnClickListener(v -> {
            if (isServiceRunning(SensorForegroundService.class)) {
                stopBackgroundService(); // Detiene el servicio
            } else {
                Toast.makeText(this, "El sensado no está activo", Toast.LENGTH_SHORT).show();
            }
        });

        // Botón "Ver Archivos"
        btnVerArchivos.setOnClickListener(v -> {
            Intent intent = new Intent(FormActivity.this, ListActivity.class);
            startActivity(intent);
        });

    }

    /** VERIFICA SI EL USUARIO ESTÁ AUTENTICADO PARA VER ARCHIVOS
    private void checkUserLoginStatus() {
        SharedPreferences prefs = getSharedPreferences("LOGIN_ARCHIVOS", MODE_PRIVATE);
        boolean estaLogueado = prefs.getBoolean("estaLogueado", false);

        if (estaLogueado) {
            startActivity(new Intent(this, ListActivity.class)); // Muestra archivos
        } else {
            startActivity(new Intent(this, LoginArchivosActivity.class)); // Redirige a login
            Toast.makeText(this, "Autenticación requerida", Toast.LENGTH_SHORT).show();
        }
    }**/

    // VALIDA QUE LOS CAMPOS REQUERIDOS ESTÉN COMPLETOS
    // VALIDA QUE LOS CAMPOS REQUERIDOS ESTÉN COMPLETOS
    private boolean validateFields() {
        if (statusRadioGroup.getCheckedRadioButtonId() == -1) {
            Toast.makeText(this, "Por favor, seleccione su estado actual (Ej. En Origen)", Toast.LENGTH_SHORT).show();
            return false;
        }
        // Ya no validamos la unidad ni la ruta aquí.
        return true;
    }


    // VERIFICA PERMISOS ANTES DE INICIAR EL SERVICIO
    private void checkPermissionsAndStartService() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, LOCATION_PERMISSION_REQUEST_CODE);
            return;
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_BACKGROUND_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.ACCESS_BACKGROUND_LOCATION}, BACKGROUND_LOCATION_PERMISSION_REQUEST_CODE);
            return;
        }

        startBackgroundService(); // Inicia el servicio si los permisos están concedidos
    }

    // INICIA EL SERVICIO EN PRIMER PLANO
    // INICIA EL SERVICIO EN PRIMER PLANO
    private void startBackgroundService() {
        if (!checkPermissions()) {
            requestPermissions();
            return;
        }

        // Verifica optimización de batería (Android 6.0+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
            if (!powerManager.isIgnoringBatteryOptimizations(getPackageName())) {
                showBatteryOptimizationDialog();
                return;
            }
        }

        // Verifica si el GPS está activado
        LocationManager locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
        if (!locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
            showEnableLocationDialog();
            return;
        }

        // Guarda el tiempo de inicio del sensado
        long startTime = System.currentTimeMillis();
        SharedPreferences prefsTime = getSharedPreferences("sensado_prefs", MODE_PRIVATE);
        prefsTime.edit().putLong("start_timestamp", startTime).apply();
        prefsTime.edit().remove("end_timestamp").apply(); // Limpia cualquier valor previo
        Log.d(TAG, "📍 Inicio de sensado guardado: " + startTime);

        try {
            Intent serviceIntent = new Intent(this, SensorForegroundService.class);
            serviceIntent.setAction("START_SENSING");

            // --- INICIO DE LA LÓGICA MODIFICADA ---

            // Obtiene los datos desde los AutoCompleteTextView
            currentRuta = getNumericIdFromAutoComplete(spinnerRuta);
            currentUnidad = editUnidad.getText().toString().trim();
            currentTipoTransp = getNumericIdFromAutoComplete(spinnerTipoTransp);

            // Guardamos en SharedPreferences lo que tengamos hasta ahora.
            // El servicio leerá esto si necesita la información más actualizada.
            SharedPreferences prefs = getSharedPreferences("SENSADO", MODE_PRIVATE);
            prefs.edit()
                    .putString("route_id", currentRuta)
                    .putString("unit_id", currentUnidad)
                    .putString("vehicle_type_id", currentTipoTransp)
                    .apply();

            // Pasa parámetros al servicio
            serviceIntent.putExtra("ruta", currentRuta);
            serviceIntent.putExtra("rutaNombre", spinnerRuta.getText().toString().trim());
            serviceIntent.putExtra("tipoTransporte", currentTipoTransp);
            serviceIntent.putExtra("unidad", currentUnidad);
            serviceIntent.putExtra("estadoPasajero", getSelectedPassengerState());
            serviceIntent.putExtra("campaign_uuid", campaignUuidSeleccionado);
            
            SharedPreferences authPrefs = getSharedPreferences("AUTH", MODE_PRIVATE);
            serviceIntent.putExtra("campaniaNombre", authPrefs.getString("campania_activa", ""));
            
            serviceIntent.putStringArrayListExtra("sensors", selectedSensors);
            Log.i(TAG, "Iniciando servicio con datos (pueden estar incompletos): Ruta=" + currentRuta + ", Unidad=" + currentUnidad);

            // --- FIN DE LA LÓGICA MODIFICADA ---

            // Inicia el servicio (compatible con Android 8.0+)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent);
            } else {
                startService(serviceIntent);
            }

            Toast.makeText(this, "Sensado iniciado. Completa los datos al abordar.", Toast.LENGTH_LONG).show();

            // Vibración al iniciar (solo una vez)
            Vibrator vibrator = (Vibrator) getSystemService(VIBRATOR_SERVICE);
            if (vibrator != null && vibrator.hasVibrator()) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(1500, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    vibrator.vibrate(1500);
                }
            }

            updateUIForRunningState(true); // Actualiza la UI
        } catch (Exception e) {
            Toast.makeText(this, "Error al iniciar el servicio: " + e.getMessage(), Toast.LENGTH_LONG).show();
            Log.e(TAG, "Error al iniciar servicio", e);
        }
    }


    // DETIENE EL SERVICIO DE SENSADO
    // DETIENE EL SERVICIO DE SENSADO
    // DETIENE EL SERVICIO DE SENSADO
    private void stopBackgroundService() {
        // Guarda el tiempo de fin del sensado
        long endTime = System.currentTimeMillis();
        SharedPreferences prefsTime = getSharedPreferences("sensado_prefs", MODE_PRIVATE);
        prefsTime.edit().putLong("end_timestamp", endTime).apply();
        Log.d(TAG, "📍 Fin de sensado guardado: " + endTime);

        // --- ACTUALIZACIÓN: Leer datos ACTUALES de la interfaz en tiempo real ---
        String rutaUI = getNumericIdFromAutoComplete(spinnerRuta);
        String unidadUI = editUnidad.getText().toString().trim();
        String tipoUI = getNumericIdFromAutoComplete(spinnerTipoTransp);

        // Guardamos en SharedPreferences lo que tenemos en la pantalla ahora mismo
        SharedPreferences prefs = getSharedPreferences("SENSADO", MODE_PRIVATE);
        prefs.edit()
                .putString("route_id", rutaUI)
                .putString("unit_id", unidadUI)
                .putString("vehicle_type_id", tipoUI)
                .apply();

        // Validar si los datos están incompletos (usando lo que está en la pantalla)
        if (rutaUI.isEmpty() || rutaUI.equals("0") || unidadUI.isEmpty() || tipoUI.isEmpty() || tipoUI.equals("0")) {
            // Si falta algo, mostramos el diálogo pasando lo que SI tenemos en la pantalla
            showCompleteDataBeforeStopDialog(rutaUI, unidadUI, tipoUI);
            return;
        }

        // Si los datos están completos, procedemos a detener el servicio.
        String rutaNombreUI = spinnerRuta.getText().toString().trim();
        finalizeStopService(rutaUI, rutaNombreUI, unidadUI, tipoUI);
    }



    /**
     * Muestra un diálogo para forzar al usuario a completar los datos del viaje
     * antes de poder detener el sensado.
     * @param currentRoute El valor actual de la ruta.
     * @param currentUnit El valor actual de la unidad.
     * @param currentTransport El valor actual del tipo de transporte.
     */
    private void showCompleteDataBeforeStopDialog(String currentRoute, String currentUnit, String currentTransport) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Completar información del viaje");
        builder.setMessage("Para poder guardar el viaje, por favor, completa toda la información requerida.");

        // Inflar una vista personalizada para el diálogo.
        View dialogView = getLayoutInflater().inflate(R.layout.dialog_complete_data, null);
        builder.setView(dialogView);

        // Referencias a los componentes del diálogo (AutoCompleteTextView)
        AutoCompleteTextView dialogSpinnerRuta = dialogView.findViewById(R.id.dialogSpinnerRuta);
        EditText dialogEditUnidad = dialogView.findViewById(R.id.dialogEditUnidad);
        AutoCompleteTextView dialogSpinnerTransporte = dialogView.findViewById(R.id.dialogSpinnerTipoTransp);

        // Configurar adaptadores desde los originales (Casteo seguro)
        if (spinnerRuta.getAdapter() instanceof ArrayAdapter) {
            dialogSpinnerRuta.setAdapter((ArrayAdapter<String>) spinnerRuta.getAdapter());
        }
        if (spinnerTipoTransp.getAdapter() instanceof ArrayAdapter) {
            dialogSpinnerTransporte.setAdapter((ArrayAdapter<String>) spinnerTipoTransp.getAdapter());
        }

        // Comportamiento de despliegue
        dialogSpinnerRuta.setOnClickListener(v -> dialogSpinnerRuta.showDropDown());
        dialogSpinnerTransporte.setOnClickListener(v -> dialogSpinnerTransporte.showDropDown());

        // Pre-llenar con datos existentes si los hay
        if (currentRoute != null && !currentRoute.equals("0") && !currentRoute.isEmpty()) {
            setSelectionByValue(dialogSpinnerRuta, currentRoute);
        }
        if (currentUnit != null && !currentUnit.isEmpty()) {
            dialogEditUnidad.setText(currentUnit);
        }
        if (currentTransport != null && !currentTransport.equals("0") && !currentTransport.isEmpty()) {
            setSelectionByValue(dialogSpinnerTransporte, currentTransport);
        }

        builder.setCancelable(false); // El usuario no puede cancelar el diálogo
        builder.setPositiveButton("Guardar y Detener", null); // Usaremos un listener manual para evitar que el diálogo se cierre

        builder.setNegativeButton("Cancelar", (dialog, which) -> {
            // Si el usuario cancela, le recordamos que el sensado sigue activo
            Toast.makeText(this, "El sensado continúa activo. Debes completar los datos para detenerlo.", Toast.LENGTH_LONG).show();
            dialog.dismiss();
        });

        AlertDialog dialog = builder.create();

        // Listener manual para el botón positivo.
        dialog.setOnShowListener(dialogInterface -> {
            Button positiveButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            positiveButton.setOnClickListener(view -> {
                String nuevaRuta = getNumericIdFromAutoComplete(dialogSpinnerRuta);
                String nuevaUnidad = dialogEditUnidad.getText().toString().trim();
                String nuevoTipoTransp = getNumericIdFromAutoComplete(dialogSpinnerTransporte);

                if (nuevaRuta.equals("0") || nuevaUnidad.isEmpty() || nuevoTipoTransp.equals("0")) {
                    Toast.makeText(this, "Debes completar todos los campos para poder detener", Toast.LENGTH_LONG).show();
                } else {
                    // Datos validados, obtenemos el nombre de la ruta del diálogo
                    String rutaNombre = dialogSpinnerRuta.getText().toString().trim();
                    finalizeStopService(nuevaRuta, rutaNombre, nuevaUnidad, nuevoTipoTransp);
                    dialog.dismiss();
                }
            });
        });

        dialog.show();
    }

    /**
     * Contiene la lógica final para detener el servicio una vez que los datos han sido validados/completados.
     * @param ruta La ruta final validada.
     * @param unidad La unidad final validada.
     * @param tipoTransporte El tipo de transporte final validado.
     */
    private void finalizeStopService(String ruta, String rutaNombre, String unidad, String tipoTransporte) {
        // 1. Actualiza SharedPreferences con los datos finales y validados
        SharedPreferences prefs = getSharedPreferences("SENSADO", MODE_PRIVATE);
        prefs.edit()
                .putString("route_id", ruta)
                .putString("unit_id", unidad)
                .putString("vehicle_type_id", tipoTransporte)
                .apply();

        // 2. Envía el intent para detener el servicio
        Intent serviceIntent = new Intent(this, SensorForegroundService.class);
        serviceIntent.setAction("STOP_SENSING");
        // Pasa los datos finales al servicio para que los use al guardar el último punto
        serviceIntent.putExtra("ruta", ruta);
        serviceIntent.putExtra("rutaNombre", rutaNombre);
        serviceIntent.putExtra("unidad", unidad);
        serviceIntent.putExtra("tipoTransporte", tipoTransporte);
        startService(serviceIntent);

        // 3. Actualiza la interfaz de usuario
        updateUIForRunningState(false);

        // 4. Calcula duración y muestra mensaje de éxito
        SharedPreferences prefsTime = getSharedPreferences("sensado_prefs", MODE_PRIVATE);
        long startTime = prefsTime.getLong("start_timestamp", 0);
        long endTime = prefsTime.getLong("end_timestamp", System.currentTimeMillis()); // Asegura que endTime esté definido
        if (startTime > 0) {
            long duracionSegundos = (endTime - startTime) / 1000;
            Toast.makeText(this, "Sensado detenido. Duración: " + duracionSegundos + "s", Toast.LENGTH_LONG).show();
        } else {
            Toast.makeText(this, "Sensado detenido.", Toast.LENGTH_LONG).show();
        }
    }





    private void guardarEnBaseDeDatos(String rutaId, String unidad, String tipoTransp) {
        DatabaseHelper dbHelper = new DatabaseHelper(this);
        SQLiteDatabase db = dbHelper.getWritableDatabase();

        try {
            // 1. Obtener el user_id desde la base de datos
            DatabaseHelper.UserInfo userInfo = dbHelper.getCurrentUserInfo();
            int userId = -1;
            String nombreUsuario = "";
            if (userInfo != null) {
                userId = userInfo.userId;
                nombreUsuario = userInfo.userName;
            } else {
                SharedPreferences prefs = getSharedPreferences("AUTH", MODE_PRIVATE);
                userId = prefs.getInt("user_id", -1);
                nombreUsuario = prefs.getString("nombreUsuario", "");
            }

            if (userId == -1) {
                Toast.makeText(this, "Error: No se pudo identificar al usuario", Toast.LENGTH_SHORT).show();
                return;
            }

            // 2. Obtener nombres de pantalla actuales
            String rutaNombre = spinnerRuta.getText().toString().trim();
            SharedPreferences authPrefs = getSharedPreferences("AUTH", MODE_PRIVATE);
            String campaniaNombre = authPrefs.getString("campania_activa", "");

            // 3. Obtener el siguiente path_id disponible
            int pathId = dbHelper.getNextPath_id(db);
            long timestamp = System.currentTimeMillis();

            // 4. Crear ContentValues con los datos del viaje
            ContentValues values = new ContentValues();
            values.put(MetadatosContract.SesionEntry.COLUMN_PATH_ID, pathId);
            values.put(MetadatosContract.SesionEntry.COLUMN_USER_ID, userId);
            values.put(MetadatosContract.SesionEntry.COLUMN_ROUTE_NAME, rutaId);
            values.put(MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME, rutaNombre);
            values.put(MetadatosContract.SesionEntry.COLUMN_START_TIMESTAMP, timestamp);
            values.put(MetadatosContract.SesionEntry.COLUMN_END_TIMESTAMP, timestamp);
            values.put(MetadatosContract.SesionEntry.COLUMN_TRANSPORT_TYPE, tipoTransp);
            values.put(MetadatosContract.SesionEntry.COLUMN_UNIT_NUMBER, unidad);
            values.put(MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_ID, campaignUuidSeleccionado);
            values.put(MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_UUID, campaignUuidSeleccionado);
            values.put(MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME, campaniaNombre);


            // 5. Insertar en la base de datos
            long sessionId = db.insert(MetadatosContract.SesionEntry.TABLE_NAME, null, values);

            if (sessionId != -1) {
                Toast.makeText(this, "Datos guardados correctamente", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "Error al guardar los datos", Toast.LENGTH_SHORT).show();
                Log.e(TAG, "Error al insertar en la base de datos");
            }
        } catch (Exception e) {
            Toast.makeText(this, "Error al guardar: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            Log.e(TAG, "Error en guardarEnBaseDeDatos", e);
        } finally {
            if (db != null) {
                db.close();
            }
        }
    }

    /**
     * Obtiene el estado del pasajero seleccionado en formato numérico.
     *
     * String con código numérico del estado:
     *         "0" = origen
     *         "1" = Caminando a la parada
     *         "2" = Esperando
     *         "3" = Ascendiendo
     *         "4" = De pie
     *         "5" = Sentado
     *         "6" = Descendiendo
     *         "7" = Destino
     *         "8" = No seleccionado
     */
    private String getSelectedPassengerState() {

        int idSeleccionado = statusRadioGroup.getCheckedRadioButtonId();

        if (idSeleccionado == -1)
            return "0";

        RadioButton rb = findViewById(idSeleccionado);

        return rb.getTag().toString();
    }

    private void updateUIForRunningState(boolean isRunning) {
        if (isRunning) {
            progressBar.setVisibility(View.VISIBLE);
            textSensando.setVisibility(View.VISIBLE);
            btnIniciarSensado.setEnabled(false);
            btnDetenerSensado.setEnabled(true);
            btnVerArchivos.setEnabled(false);

            // Permitir cambiar solo el estado del pasajero
            spinnerRuta.setEnabled(false);
            spinnerTipoTransp.setEnabled(false);
            editUnidad.setEnabled(false);
            setRadioGroupEnabled(true); // Habilitar los RadioButtons
        } else {
            progressBar.setVisibility(View.GONE);
            textSensando.setVisibility(View.GONE);
            btnIniciarSensado.setEnabled(true);
            btnDetenerSensado.setEnabled(false);
            btnVerArchivos.setEnabled(true);

            spinnerRuta.setEnabled(true);
            spinnerTipoTransp.setEnabled(true);
            editUnidad.setEnabled(true);
            setRadioGroupEnabled(true);
        }
    }

    private void setRadioGroupEnabled(boolean enabled) {
        for (int i = 0; i < statusRadioGroup.getChildCount(); i++) {
            View child = statusRadioGroup.getChildAt(i);
            if (child instanceof RadioButton) {
                child.setEnabled(enabled);
            }
        }
    }
    private boolean checkPermissions() {
        List<String> requiredPermissions = new ArrayList<>();
        requiredPermissions.add(Manifest.permission.ACCESS_FINE_LOCATION);
        requiredPermissions.add(Manifest.permission.ACCESS_COARSE_LOCATION);

        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
            requiredPermissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            requiredPermissions.add(Manifest.permission.ACCESS_BACKGROUND_LOCATION);
        }

        for (String permission : requiredPermissions) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                return false;
            }
        }
        return true;
    }

    private void requestPermissions() {
        List<String> permissionsToRequest = new ArrayList<>();

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.ACCESS_FINE_LOCATION);
        }

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.ACCESS_COARSE_LOCATION);
        }

        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                        != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                        != PackageManager.PERMISSION_GRANTED) {
            permissionsToRequest.add(Manifest.permission.ACCESS_BACKGROUND_LOCATION);
        }

        if (!permissionsToRequest.isEmpty()) {
            ActivityCompat.requestPermissions(
                    this,
                    permissionsToRequest.toArray(new String[0]),
                    LOCATION_PERMISSION_REQUEST_CODE);
        }
    }
    private boolean isServiceRunning(Class<?> serviceClass) {
        ActivityManager manager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        for (ActivityManager.RunningServiceInfo service : manager.getRunningServices(Integer.MAX_VALUE)) {
            if (serviceClass.getName().equals(service.service.getClassName())) {
                return true;
            }
        }
        return false;
    }
    private void showBatteryOptimizationDialog() {
        new AlertDialog.Builder(this)
                .setTitle("Optimización de Batería")
                .setMessage("Para un funcionamiento óptimo, por favor desactiva la optimización de batería para esta aplicación.")
                .setPositiveButton("Configurar", (dialog, which) -> {
                    try {
                        Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                        intent.setData(Uri.parse("package:" + getPackageName()));
                        startActivityForResult(intent, REQUEST_CODE_BATTERY_OPTIMIZATIONS);
                    } catch (Exception e) {
                        Toast.makeText(this, "No se pudo abrir la configuración", Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("Más tarde", null)
                .show();
    }
    private void showEnableLocationDialog() {
        new AlertDialog.Builder(this)
                .setTitle("GPS Desactivado")
                .setMessage("El sensado requiere que actives los servicios de ubicación.")
                .setPositiveButton("Activar GPS", (dialog, which) -> {
                    try {
                        Intent intent = new Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS);
                        startActivityForResult(intent, REQUEST_CODE_LOCATION_SETTINGS);
                    } catch (Exception e) {
                        Toast.makeText(this, "No se pudo abrir la configuración", Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_CODE_BATTERY_OPTIMIZATIONS) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
                if (powerManager.isIgnoringBatteryOptimizations(getPackageName())) {
                    startBackgroundService();
                }
            }
        } else if (requestCode == REQUEST_CODE_LOCATION_SETTINGS) {
            LocationManager locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                startBackgroundService();
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == LOCATION_PERMISSION_REQUEST_CODE ||
                requestCode == BACKGROUND_LOCATION_PERMISSION_REQUEST_CODE) {

            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                if (validateFields()) {
                    startBackgroundService();
                }
            } else {
                Toast.makeText(this, "Permiso necesario para el sensado", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @SuppressLint("UnspecifiedRegisterReceiverFlag") // Solo si es necesario
    @Override
    protected void onResume() {
        super.onResume();

        // Sincronizar UI con el estado del servicio al volver a la actividad
        boolean isRunning = isServiceRunning(SensorForegroundService.class);
        if (isRunning) {
            restaurarDatosDeSensado();
        }
        updateUIForRunningState(isRunning);

        IntentFilter filter = new IntentFilter("SENSADO_COMPLETADO");

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // Para Android 13+ (API 33+)
            registerReceiver(sensadoReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            // Versiones anteriores
            registerReceiver(sensadoReceiver, filter);
        }
    }
    //permisos app para el funcionamionento que tiene que otorgar el usuario
    private void checkRequiredPermissions() {
        List<String> permissionsNeeded = new ArrayList<>();

        permissionsNeeded.add(Manifest.permission.ACCESS_FINE_LOCATION);
        permissionsNeeded.add(Manifest.permission.ACCESS_COARSE_LOCATION);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissionsNeeded.add(Manifest.permission.POST_NOTIFICATIONS);
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            // Permisos específicos de Android 15 (API 34) de la app  para el funcionamien to
            permissionsNeeded.add(Manifest.permission.FOREGROUND_SERVICE_LOCATION);
        }

        // Verificar y solicitar permisos faltantes
        List<String> permissionsToRequest = new ArrayList<>();
        for (String permission : permissionsNeeded) {
            if (ContextCompat.checkSelfPermission(this, permission) != PackageManager.PERMISSION_GRANTED) {
                permissionsToRequest.add(permission);
            }
        }

        if (!permissionsToRequest.isEmpty()) {
            ActivityCompat.requestPermissions(this,
                    permissionsToRequest.toArray(new String[0]),
                    REQUEST_CODE_REQUIRED_PERMISSIONS);
        }
    }

    private void showPermissionDeniedDialog() {
        new AlertDialog.Builder(this)
                .setTitle("Permisos requeridos")
                .setMessage("La aplicación necesita ciertos permisos para funcionar correctamente.")
                .setPositiveButton("Configurar permisos", (dialog, which) -> {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                    intent.setData(Uri.fromParts("package", getPackageName(), null));
                    startActivity(intent);
                })
                .setNegativeButton("Salir", (dialog, which) -> finish())
                .setCancelable(false)
                .show();
    }

    @Override
    public void onBackPressed() {
        if (isServiceRunning(SensorForegroundService.class)) {
            Toast.makeText(this, "Debe detener el sensado antes de regresar", Toast.LENGTH_SHORT).show();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        try {
            unregisterReceiver(sensadoReceiver);
        } catch (IllegalArgumentException e) {
            Log.w(TAG, "Receiver no estaba registrado");
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
    }

    /**
     * Extrae el número de ID de un Spinner con formato "1 - Texto descriptivo".
     * Si no hay selección válida, devuelve "0".
     */
    private String getNumericIdFromAutoComplete(AutoCompleteTextView autoComplete) {
        String item = autoComplete.getText().toString().trim();
        if (item.isEmpty()) return "0";
        
        // Caso 1: Ya tiene el formato "ID - Nombre"
        if (item.contains("-")) {
            String[] parts = item.split("-");
            try {
                return parts[0].trim();
            } catch (Exception e) {
                return "0";
            }
        }
        
        // Caso 2: Solo escribieron el nombre, buscamos en el adaptador
        if (autoComplete.getAdapter() != null) {
            for (int i = 0; i < autoComplete.getAdapter().getCount(); i++) {
                String adapterItem = (String) autoComplete.getAdapter().getItem(i);
                if (adapterItem.toLowerCase().contains(item.toLowerCase()) && adapterItem.contains("-")) {
                    return adapterItem.split("-")[0].trim();
                }
            }
        }
        
        return "0";
    }

}
