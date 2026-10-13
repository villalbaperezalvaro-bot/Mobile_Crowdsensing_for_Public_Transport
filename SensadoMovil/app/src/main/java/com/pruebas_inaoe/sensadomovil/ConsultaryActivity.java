package com.pruebas_inaoe.sensadomovil;

import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.text.Spannable;
import android.text.SpannableStringBuilder;
import android.text.style.ForegroundColorSpan;
import android.widget.Button;
import android.widget.TextView;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ConsultaryActivity extends AppCompatActivity {

    private TextView etDatosApi;
    private Button btnAceptar;
    private OkHttpClient client;
    private String token;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_consultary);

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        etDatosApi = findViewById(R.id.etDatosApi);
        btnAceptar = findViewById(R.id.btnAceptar);
        client = new OkHttpClient();

        // 🔹 Obtener token del login guardado
        SharedPreferences prefs = getSharedPreferences("AUTH", MODE_PRIVATE);
        token = prefs.getString("token", "");

        if (token.isEmpty()) {
            etDatosApi.setText("⚠️ No se encontró token. Inicia sesión nuevamente.");
        } else {
            fetchCampaigns(); // 🔹 Consultar campañas
        }

        btnAceptar.setOnClickListener(v -> {
            Intent intent = new Intent(ConsultaryActivity.this, CampanaActivity.class);
            startActivity(intent);
            finish();
        });
    }

    /**
     * 🔹 Llama al endpoint de campañas:
     * POST http://hu-api.rutamovil.com.mx/api/admin/campaign/get
     */
    private void fetchCampaigns() {
        String url = "https://hu-api.rutamovil.com.mx/api/user/sensed_data/get";

        // En este endpoint no se envía cuerpo, solo el POST vacío
        RequestBody body = RequestBody.create("", MediaType.parse("application/json; charset=utf-8"));

        Request request = new Request.Builder()
                .url(url)
                .post(body)
                .addHeader("Authorization", "Bearer " + token)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                runOnUiThread(() ->
                        etDatosApi.setText("❌ Error al conectar con el servidor:\n" + e.getMessage()));
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                String json = response.body() != null ? response.body().string() : "{}";

                runOnUiThread(() -> {
                    if (response.isSuccessful()) {
                        etDatosApi.setText(colorizeJson(formatJson(json)));
                    } else {
                        etDatosApi.setText("⚠️ Error " + response.code() + ":\n" + json);
                    }
                });
            }
        });
    }

    // 🔹 Formatear JSON para mostrar bonito
    private String formatJson(String json) {
        try {
            if (json.trim().startsWith("{")) {
                return new JSONObject(json).toString(4);
            } else if (json.trim().startsWith("[")) {
                return new JSONArray(json).toString(4);
            }
        } catch (Exception ignored) {}
        return json;
    }

    // 🔹 Colorear el JSON en pantalla
    private SpannableStringBuilder colorizeJson(String json) {
        SpannableStringBuilder spannable = new SpannableStringBuilder(json);

        applyColor("\"(.*?)\"(?=\\s*:)", Color.parseColor("#65D46E"), spannable); // Claves
        applyColor(":\\s*\"(.*?)\"", Color.parseColor("#EBCB8B"), spannable);     // Strings
        applyColor(":\\s*\\d+(\\.\\d+)?", Color.parseColor("#81A1C1"), spannable); // Números
        applyColor("\\b(true|false|null)\\b", Color.parseColor("#81A1C1"), spannable); // Boolean/null
        applyColor("[{}\\[\\]]", Color.parseColor("#D8DEE9"), spannable);        // Llaves/corchetes

        return spannable;
    }

    private void applyColor(String regex, int color, SpannableStringBuilder spannable) {
        Matcher matcher = Pattern.compile(regex).matcher(spannable);
        while (matcher.find()) {
            spannable.setSpan(new ForegroundColorSpan(color),
                    matcher.start(), matcher.end(), Spannable.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
    }
}
