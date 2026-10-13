package com.pruebas_inaoe.sensadomovil;

import android.Manifest;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import androidx.core.app.ActivityCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkInfo;
import androidx.work.WorkManager;
import androidx.lifecycle.Observer;

import java.util.ArrayList;
import java.util.UUID;
import java.util.concurrent.TimeUnit;


public class ListActivity extends AppCompatActivity {

    private static final int REQUEST_READ_STORAGE = 200;

    private RecyclerView rvArchivos;
    private ViajesAdapter viajesAdapter;
    private ArrayList<ViajeConArchivos> listaAgrupada;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);
        setContentView(R.layout.activity_list);

        rvArchivos = findViewById(R.id.rvArchivos);
        rvArchivos.setLayoutManager(new LinearLayoutManager(this));

        cargarDatosYConfigurarAdapter();
        solicitarPermisoLectura();
    }

    private void cargarDatosYConfigurarAdapter() {
        DatabaseHelper dbHelper = new DatabaseHelper(this);
        listaAgrupada = dbHelper.obtenerViajesConArchivos();

        viajesAdapter = new ViajesAdapter(
                listaAgrupada,
                (viaje, position, tokenNuevo) ->
                        sincronizarViaje(viaje, position)
        );

        rvArchivos.setAdapter(viajesAdapter);
    }

    /**
     * 🔥 NUEVA SINCRONIZACIÓN PROFESIONAL CON WORKMANAGER
     */
    private void sincronizarViaje(ViajeConArchivos viaje, int position) {

        SharedPreferences prefs = getSharedPreferences("AUTH", MODE_PRIVATE);

        String token = prefs.getString("token", null);
        int userId = prefs.getInt("user_id", -1);
        String campaignUuid = prefs.getString("campaign_uuid", null);

        if (token == null || userId == -1 || campaignUuid == null) {
            Toast.makeText(this,
                    "Debes iniciar sesión y seleccionar campaña",
                    Toast.LENGTH_LONG).show();
            return;
        }

        // 🔹 Restricción: solo con internet
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();

        // 🔹 Pasamos el path_id al Worker
        Data inputData = new Data.Builder()
                .putInt(SyncViajeWorker.KEY_PATH_ID, viaje.pathId)
                .build();

        OneTimeWorkRequest workRequest =
                new OneTimeWorkRequest.Builder(SyncViajeWorker.class)
                        .setConstraints(constraints)
                        .setInputData(inputData)
                        .setBackoffCriteria(
                                BackoffPolicy.EXPONENTIAL,
                                30,
                                TimeUnit.SECONDS
                        )
                        .build();

        WorkManager.getInstance(this).enqueue(workRequest);

        // 🔹 Observar el resultado para refrescar la lista
        WorkManager.getInstance(this).getWorkInfoByIdLiveData(workRequest.getId())
                .observe(this, workInfo -> {
                    if (workInfo != null && workInfo.getState().isFinished()) {
                        cargarDatosYConfigurarAdapter(); // Refrescar lista al terminar
                    }
                });

        Toast.makeText(this,
                "Sincronización en segundo plano iniciada",
                Toast.LENGTH_LONG).show();
    }

    private void solicitarPermisoLectura() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
                checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE)
                        != PackageManager.PERMISSION_GRANTED) {

            ActivityCompat.requestPermissions(
                    this,
                    new String[]{Manifest.permission.READ_EXTERNAL_STORAGE},
                    REQUEST_READ_STORAGE
            );
        }
    }
}
