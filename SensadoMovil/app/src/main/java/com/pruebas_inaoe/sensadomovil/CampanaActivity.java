package com.pruebas_inaoe.sensadomovil;

import android.content.Intent;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.util.Log;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.pruebas_inaoe.sensadomovil.api.ApiService;
import com.pruebas_inaoe.sensadomovil.api.RetrofitClient;

import java.util.ArrayList;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class CampanaActivity extends AppCompatActivity {

    private RecyclerView rvCampaigns;
    private CampaignAdapter campaignAdapter;
    private EditText etSearchCampaign;
    private TextView tvEmptyState;
    private DatabaseHelper dbHelper;

    private List<Campaign> originalCampaignList = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_campana);

        rvCampaigns = findViewById(R.id.rvCampaigns);
        etSearchCampaign = findViewById(R.id.etSearchCampaign);
        tvEmptyState = findViewById(R.id.tvEmptyState);
        dbHelper = new DatabaseHelper(this);

        setupRecyclerView();
        setupSearchListener();
        cargarCampanasDesdeBackend();
    }

    private void setupRecyclerView() {
        rvCampaigns.setLayoutManager(new LinearLayoutManager(this));
        campaignAdapter = new CampaignAdapter(new ArrayList<>(), campaign -> {
            // Lógica al presionar "Participar"
            seleccionarCampana(campaign);
        });
        rvCampaigns.setAdapter(campaignAdapter);
    }

    private void setupSearchListener() {
        etSearchCampaign.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                campaignAdapter.getFilter().filter(s);
            }

            @Override
            public void afterTextChanged(Editable s) {}
        });
    }

    private void seleccionarCampana(Campaign campaign) {
        // Lógica de intercalado para JSON (Temporal hasta nuevo endpoint)
        String jsonFile = "estados.json";
        for (int i = 0; i < originalCampaignList.size(); i++) {
            if (originalCampaignList.get(i).uuid.equals(campaign.uuid)) {
                jsonFile = (i % 2 == 0) ? "estados.json" : "estados2.json";
                break;
            }
        }

        // Guardar selección localmente
        getSharedPreferences("AUTH", MODE_PRIVATE)
                .edit()
                .putString("campania_activa", campaign.name)
                .putString("campaign_uuid", campaign.uuid)
                .putString("config_json_file", jsonFile)
                .apply();

        Toast.makeText(this,
                "Seleccionaste campaña: " + campaign.name + "\nUsando: " + jsonFile,
                Toast.LENGTH_LONG).show();

        startActivity(new Intent(this, FormActivity.class));
    }

    // Obtener campañas del backend
    private void cargarCampanasDesdeBackend() {
        ApiService apiService = RetrofitClient.getApiService();
        String token = getSharedPreferences("AUTH", MODE_PRIVATE).getString("token", null);

        if (token == null) {
            Toast.makeText(this, "Debes iniciar sesión nuevamente", Toast.LENGTH_LONG).show();
            startActivity(new Intent(this, MainActivity.class));
            finish();
            return;
        }

        token = "Bearer " + token;

        apiService.getCampaigns(token).enqueue(new Callback<CampaignResponse>() {
            @Override
            public void onResponse(Call<CampaignResponse> call, Response<CampaignResponse> response) {
                if (response.isSuccessful() && response.body() != null && response.body().status) {
                    List<Campaign> campaigns = response.body().data;
                    guardarCampanasLocal(campaigns);
                    cargarCampanasDesdeBD();
                } else {
                    cargarCampanasDesdeBD();
                }
            }

            @Override
            public void onFailure(Call<CampaignResponse> call, Throwable t) {
                Log.e("API", "Error de conexión: " + t.getMessage());
                cargarCampanasDesdeBD();
            }
        });
    }

    // Guardar campañas en SQLite
    private void guardarCampanasLocal(List<Campaign> campaigns) {
        SQLiteDatabase db = dbHelper.getWritableDatabase();
        db.delete(MetadatosContract.CampaignEntry.TABLE_NAME, null, null);

        for (Campaign c : campaigns) {
            db.execSQL("INSERT OR REPLACE INTO " + MetadatosContract.CampaignEntry.TABLE_NAME +
                            " (campaign_uuid, campaign_name, description) VALUES (?, ?, ?)",
                    new Object[]{c.uuid, c.name, c.description});
        }

        db.close();
    }

    // Cargar campañas desde SQLite
    private void cargarCampanasDesdeBD() {
        originalCampaignList.clear();

        SQLiteDatabase db = dbHelper.getReadableDatabase();
        Cursor cursor = db.query(
                MetadatosContract.CampaignEntry.TABLE_NAME,
                new String[]{
                        MetadatosContract.CampaignEntry.COLUMN_CAMPAIGN_UUID,
                        MetadatosContract.CampaignEntry.COLUMN_CAMPAIGN_NAME,
                        MetadatosContract.CampaignEntry.COLUMN_DESCRIPTION
                },
                null, null, null, null, null
        );

        while (cursor.moveToNext()) {
            Campaign c = new Campaign();
            c.uuid = cursor.getString(0);
            c.name = cursor.getString(1);
            c.description = cursor.getString(2);
            originalCampaignList.add(c);
        }

        cursor.close();
        db.close();

        if (originalCampaignList.isEmpty()) {
            tvEmptyState.setVisibility(View.VISIBLE);
            rvCampaigns.setVisibility(View.GONE);
        } else {
            tvEmptyState.setVisibility(View.GONE);
            rvCampaigns.setVisibility(View.VISIBLE);
            campaignAdapter.updateList(originalCampaignList);
        }
    }
}
