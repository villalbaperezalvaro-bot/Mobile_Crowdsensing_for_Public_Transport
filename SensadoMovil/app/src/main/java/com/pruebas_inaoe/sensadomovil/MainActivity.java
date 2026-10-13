package com.pruebas_inaoe.sensadomovil;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import com.google.android.material.textfield.TextInputEditText;
import android.widget.Toast;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import org.json.JSONObject;
import java.io.IOException;

public class MainActivity extends AppCompatActivity {

    private static final String TAG = "MainActivity";
    private TextInputEditText emailEditText, passwordEditText;
    private final OkHttpClient client = new OkHttpClient();
    // rura para haceder a la API de rutamovil
    private static final String LOGIN_URL = "https://hu-api.rutamovil.com.mx/api/auth/login";
    private static final String PREF_FIRST_RUN = "first_run";
    private SharedPreferences sharedPreferences;
    private Button enterButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);

        // Inicializar SharedPreferences
        sharedPreferences = getSharedPreferences("APP_PREFS", MODE_PRIVATE);

        // Verificar si NO es la primera ejecución
        if (!sharedPreferences.getBoolean(PREF_FIRST_RUN, true)) {
            DatabaseHelper dbHelper = new DatabaseHelper(this);
            DatabaseHelper.UserInfo userInfo = dbHelper.getCurrentUserInfo();

            if (userInfo != null) {
                goToCampanaActivity();
                return;
            } else {
                sharedPreferences.edit().putBoolean(PREF_FIRST_RUN, true).apply();
            }
        }

        setContentView(R.layout.activity_main);

        enterButton = findViewById(R.id.enterButton);
        emailEditText = findViewById(R.id.emailEditText);
        passwordEditText = findViewById(R.id.passwordEditText);

        enterButton.setOnClickListener(v -> {
            String email = emailEditText.getText().toString().trim();
            String password = passwordEditText.getText().toString().trim();

            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(MainActivity.this, "Por favor completa todos los campos", Toast.LENGTH_SHORT).show();
            } else {
                realizarLogin(email, password);
            }
        });
    }
    /**
    private void goToCampanaActivity() {
        Intent intent = new Intent(this, camaign_tipo.class);
        startActivity(intent);
        finish();
    }
*/
    private void goToCampanaActivity() {
        Intent intent = new Intent(this, CampanaActivity.class);
        startActivity(intent);
        finish();
    }

    private void realizarLogin(String email, String password) {
        JSONObject json = new JSONObject();
        try {
            json.put("email", email);
            json.put("password", password);
        } catch (Exception e) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, "Error al crear JSON", Toast.LENGTH_SHORT).show());
            return;
        }

        RequestBody body = RequestBody.create(
                json.toString(),
                MediaType.parse("application/json; charset=utf-8")
        );

        Request request = new Request.Builder()
                .url(LOGIN_URL)
                .post(body)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                Log.e(TAG, "Error en la conexión: " + e.getMessage());
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "No se pudo conectar al servidor", Toast.LENGTH_LONG).show());
            }

            @Override
            public void onResponse(Call call, Response response) {
                try {
                    String responseBody = response.body() != null ? response.body().string() : "{}";
                    Log.d(TAG, "Respuesta del servidor: " + responseBody);

                    JSONObject jsonResponse = new JSONObject(responseBody);

                    if (!jsonResponse.has("status")) {
                        throw new Exception("La respuesta no contiene el campo 'status'");
                    }

                    boolean status = jsonResponse.getBoolean("status");

                    if (status) {
                        if (!jsonResponse.has("data")) {
                            throw new Exception("La respuesta no contiene el campo 'data'");
                        }

                        JSONObject data = jsonResponse.getJSONObject("data");
                        String token = data.getString("access_token");
                        JSONObject user = data.getJSONObject("user");

                        int userId = user.getInt("id");
                        String nombreUsuario = user.getString("first_name") + " " + user.getString("last_name");

                        // 🔹 NUEVO: obtener campaign_uuid si existe
                       // String campaignUuid = data.has("campaign_uuid") ? data.getString("campaign_uuid") : null;
                        // 🔹 Obtener campaign_uuid desde user.campaigns[0].uuid si existe
                        String campaignUuid = null;
                        String campaignName = null;

                        if (user.has("campaigns")) {
                            var campaignsArray = user.getJSONArray("campaigns");
                            if (campaignsArray.length() > 0) {
                                JSONObject firstCampaign = campaignsArray.getJSONObject(0);
                                campaignUuid = firstCampaign.optString("uuid", null);
                                campaignName = firstCampaign.optString("name", "Campaña sin nombre");
                            }
                        }

                        // 1. Guardar en SharedPreferences (AUTH)
                        SharedPreferences.Editor editor = getSharedPreferences("AUTH", MODE_PRIVATE).edit();
                        editor.putString("token", token);
                        editor.putString("nombreUsuario", nombreUsuario);
                        editor.putInt("user_id", userId);
                        editor.putString("email", email);
                        editor.putString("password", password);

                       /** if (campaignUuid != null && !campaignUuid.isEmpty()) {
                            editor.putString("campaign_uuid", campaignUuid);
                            Log.i(TAG, "UUID de campaña guardado: " + campaignUuid);
                        }**/

                        if (campaignUuid != null && !campaignUuid.isEmpty()) {
                            editor.putString("campaign_uuid", campaignUuid);
                            editor.putString("campania_activa", campaignName);
                            Log.i(TAG, "UUID de campaña guardado: " + campaignUuid + " (" + campaignName + ")");
                        }

                        editor.apply();

                        // 2. Guardar en BD local
                        DatabaseHelper dbHelper = new DatabaseHelper(MainActivity.this);
                        long result = dbHelper.saveOrUpdateUser(userId, nombreUsuario, email);

                        if (result != -1) {
                            Log.i(TAG, "Usuario guardado en BD con ID: " + userId);
                        } else {
                            Log.e(TAG, "Error al guardar usuario en BD");
                        }

                        // 3. Actualizar bandera de primera ejecución
                        sharedPreferences.edit()
                                .putBoolean(PREF_FIRST_RUN, false)
                                .apply();

                        runOnUiThread(() -> {
                            Toast.makeText(MainActivity.this, "¡Bienvenido " + nombreUsuario + "!", Toast.LENGTH_SHORT).show();
                            goToCampanaActivity();
                        });
                    } else {
                        String errorMsg = jsonResponse.optString("message", "Credenciales incorrectas");
                        runOnUiThread(() -> Toast.makeText(MainActivity.this, errorMsg, Toast.LENGTH_LONG).show());
                    }
                } catch (Exception e) {
                    Log.e(TAG, "Error procesando respuesta: " + e.getMessage(), e);
                    runOnUiThread(() -> {
                        Toast.makeText(MainActivity.this, "Error en el formato de la respuesta: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    });
                } finally {
                    if (response.body() != null) {
                        response.body().close();
                    }
                }
            }
        });
    }
}
