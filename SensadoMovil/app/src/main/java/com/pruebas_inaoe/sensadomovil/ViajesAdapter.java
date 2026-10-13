package com.pruebas_inaoe.sensadomovil;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.content.FileProvider;
import androidx.recyclerview.widget.RecyclerView;



import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import okhttp3.MediaType;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;

import com.pruebas_inaoe.sensadomovil.api.ApiService;
import com.pruebas_inaoe.sensadomovil.api.RetrofitClient;

import retrofit2.Call;


public class ViajesAdapter extends RecyclerView.Adapter<ViajesAdapter.ViajeViewHolder> {

    // 🔹 Cambiado a public para permitir acceso desde ListActivity
    public final ArrayList<ViajeConArchivos> listaViajes;

    private static final String PREF_NAME = "AUTH";
    private static final String PREF_EMAIL = "email";
    private static final String PREF_PASSWORD = "password";
    private static final String PREF_TOKEN = "token";

    public interface OnSincronizarClickListener {
        void onSincronizarClick(ViajeConArchivos viaje, int position, String token);
    }

    private final OnSincronizarClickListener sincronizarListener;

    public ViajesAdapter(ArrayList<ViajeConArchivos> listaViajes, OnSincronizarClickListener listener) {
        this.listaViajes = listaViajes;
        this.sincronizarListener = listener;
    }

    @NonNull
    @Override
    public ViajeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View vista = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_viaje, parent, false);
        return new ViajeViewHolder(vista);
    }

    private String obtenerNombreDesdeRuta(String ruta, Context context) {
        if (ruta == null) return "";
        if (ruta.startsWith("content://")) {
            Uri uri = Uri.parse(ruta);
            String nombre = null;
            try (Cursor cursor = context.getContentResolver().query(uri, null, null, null, null)) {
                if (cursor != null && cursor.moveToFirst()) {
                    int nameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME);
                    if (nameIndex != -1) {
                        nombre = cursor.getString(nameIndex);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            return (nombre != null) ? nombre : ruta;
        } else {
            int index = ruta.lastIndexOf('/');
            return (index != -1 && index < ruta.length() - 1) ? ruta.substring(index + 1) : ruta;
        }
    }

    @Override
    public void onBindViewHolder(@NonNull ViajeViewHolder holder, int position) {
        ViajeConArchivos viaje = listaViajes.get(position);
        Context context = holder.itemView.getContext();

        String rutaAMostrar = (viaje.rutaNombre != null && !viaje.rutaNombre.isEmpty()) ? viaje.rutaNombre : ("Ruta: " + viaje.ruta);
        if (!rutaAMostrar.toLowerCase().contains("ruta")) {
            holder.tvRuta.setText("Ruta: " + rutaAMostrar);
        } else {
            holder.tvRuta.setText(rutaAMostrar);
        }
        
        TextView tvCampaign = holder.itemView.findViewById(R.id.tvcampaign);
        String campaniaAMostrar = (viaje.campaniaNombre != null && !viaje.campaniaNombre.isEmpty()) ? viaje.campaniaNombre : viaje.campaignUuid;
        tvCampaign.setText("Campaña: " + campaniaAMostrar);
        /**TextView tvVoluntario = holder.itemView.findViewById(R.id.tvVoluntario);
        tvVoluntario.setText("Voluntario: " + viaje.voluntario);**/



        holder.archivosContainer.removeAllViews();

        int sincronizados = 0;
        int pendientes = 0;

        for (ViajeConArchivos.ArchivoSync archivoSync : viaje.archivos) {
            String nombreMostrado = obtenerNombreDesdeRuta(archivoSync.nombreArchivo, context);
            String estado = archivoSync.estado;

            View archivoView = LayoutInflater.from(context)
                    .inflate(R.layout.item_archivo, holder.archivosContainer, false);
            TextView tvNombreArchivo = archivoView.findViewById(R.id.tvNombreArchivo);
            TextView tvStatusArchivo = archivoView.findViewById(R.id.tvStatusArchivo);

            tvNombreArchivo.setText(nombreMostrado);
            tvNombreArchivo.setTextColor(context.getResources().getColor(R.color.blue));
            tvNombreArchivo.setOnClickListener(v -> abrirArchivo(context, archivoSync.nombreArchivo));

            if (archivoSync.errorMsg != null && !archivoSync.errorMsg.isEmpty()) {
                tvStatusArchivo.setText("Ver error");
                tvStatusArchivo.setTextColor(context.getResources().getColor(android.R.color.holo_red_dark));
                tvStatusArchivo.setPaintFlags(tvStatusArchivo.getPaintFlags() | android.graphics.Paint.UNDERLINE_TEXT_FLAG);
                tvStatusArchivo.setOnClickListener(v -> {
                    new androidx.appcompat.app.AlertDialog.Builder(context)
                            .setTitle("Detalle del Error")
                            .setMessage(archivoSync.errorMsg)
                            .setPositiveButton("Cerrar", null)
                            .show();
                });
            } else {
                tvStatusArchivo.setText(estado);
                tvStatusArchivo.setOnClickListener(null);
                tvStatusArchivo.setPaintFlags(tvStatusArchivo.getPaintFlags() & (~android.graphics.Paint.UNDERLINE_TEXT_FLAG));
                switch (estado) {
                    case "Pendiente":
                        tvStatusArchivo.setTextColor(context.getResources().getColor(android.R.color.holo_orange_dark));
                        pendientes++;
                        break;
                    case "Sincronizado":
                        tvStatusArchivo.setTextColor(context.getResources().getColor(android.R.color.holo_green_dark));
                        sincronizados++;
                        break;
                    case "Error":
                        tvStatusArchivo.setTextColor(context.getResources().getColor(android.R.color.holo_red_dark));
                        break;
                }
            }

            archivoView.setAlpha(0f);
            archivoView.animate().alpha(1f).setDuration(300).start();

            holder.archivosContainer.addView(archivoView);
        }

        holder.tvSyncStatus.setText("Pendientes: " + pendientes + " | OK: " + sincronizados);

        if (pendientes == 0 && sincronizados > 0) {
            holder.tvSyncStatus.setTextColor(context.getResources().getColor(android.R.color.holo_green_dark));
        } else if (pendientes > 0) {
            holder.tvSyncStatus.setTextColor(context.getResources().getColor(android.R.color.holo_orange_dark));
        } else {
            holder.tvSyncStatus.setTextColor(context.getResources().getColor(android.R.color.black));
        }

        if (pendientes == 0 && sincronizados > 0) {
            holder.btnSincronizar.setEnabled(false);
            holder.btnSincronizar.setText("Sincronizado");
        } else {
            holder.btnSincronizar.setEnabled(true);
            holder.btnSincronizar.setText("Sincronizar");
        }

        holder.btnSincronizar.setOnClickListener(v -> obtenerTokenYSincronizar(context, viaje, position));
    }

    @Override
    public int getItemCount() {
        return listaViajes.size();
    }

    private void abrirArchivo(Context context, String nombreArchivo) {
        Uri uri;
        if (nombreArchivo.startsWith("content://")) {
            uri = Uri.parse(nombreArchivo);
        } else {
            File archivo = new File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS + "/SensadoMovil"), nombreArchivo);
            if (!archivo.exists()) {
                Toast.makeText(context, "Archivo no encontrado: " + archivo.getAbsolutePath(), Toast.LENGTH_SHORT).show();
                return;
            }
            uri = Build.VERSION.SDK_INT >= Build.VERSION_CODES.N
                    ? FileProvider.getUriForFile(context, context.getPackageName() + ".provider", archivo)
                    : Uri.fromFile(archivo);
        }

        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setDataAndType(uri, "text/csv");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        try {
            context.startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(context, "No se pudo abrir el archivo: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void obtenerTokenYSincronizar(Context context, ViajeConArchivos viaje, int position) {

        SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
        String email = prefs.getString(PREF_EMAIL, null);
        String password = prefs.getString(PREF_PASSWORD, null);

        if (email == null || password == null) {
            Toast.makeText(context, "No hay credenciales guardadas", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            // Crear JSON para Retrofit
            JSONObject json = new JSONObject();
            json.put("email", email);
            json.put("password", password);

            RequestBody body = RequestBody.create(
                    json.toString(),
                    okhttp3.MediaType.get("application/json; charset=utf-8")
            );

            ApiService api = RetrofitClient.getDefaultApi();

            Call<ResponseBody> call = api.login(body);

            call.enqueue(new retrofit2.Callback<ResponseBody>() {
                @Override
                public void onResponse(Call<ResponseBody> call, retrofit2.Response<ResponseBody> response) {

                    if (response.isSuccessful()) {
                        try {
                            String raw = response.body().string();
                            JSONObject res = new JSONObject(raw);

                            String token = res.getJSONObject("data").getString("access_token");

                            prefs.edit().putString(PREF_TOKEN, token).apply();

                            Toast.makeText(context, "Token renovado. Sincronizando...", Toast.LENGTH_SHORT).show();

                            // campaign_uuid
                            String campaignUuid = prefs.getString("campaign_uuid", null);
                            if (campaignUuid != null) {
                                viaje.campaignUuid = campaignUuid;
                            }

                            if (sincronizarListener != null) {
                                sincronizarListener.onSincronizarClick(viaje, position, token);
                            }

                        } catch (Exception e) {
                            Toast.makeText(context, "Error procesando login", Toast.LENGTH_SHORT).show();
                        }
                    } else {
                        Toast.makeText(context, "Login incorrecto", Toast.LENGTH_SHORT).show();
                    }
                }

                @Override
                public void onFailure(Call<ResponseBody> call, Throwable t) {
                    Toast.makeText(context, "Error de red: " + t.getMessage(), Toast.LENGTH_SHORT).show();
                }
            });

        } catch (JSONException e) {
            e.printStackTrace();
        }
    }





    private byte[] leerBytesArchivo(File file) throws IOException {
        FileInputStream fis = new FileInputStream(file);
        byte[] bytes = new byte[(int) file.length()];
        fis.read(bytes);
        fis.close();
        return bytes;
    }

    static class ViajeViewHolder extends RecyclerView.ViewHolder {
        TextView tvRuta, tvSyncStatus;
        LinearLayout archivosContainer;
        Button btnSincronizar;

        public ViajeViewHolder(@NonNull View itemView) {
            super(itemView);
            tvRuta = itemView.findViewById(R.id.tvRuta);
            archivosContainer = itemView.findViewById(R.id.archivosContainer);
            tvSyncStatus = itemView.findViewById(R.id.tvSyncStatus);
            btnSincronizar = itemView.findViewById(R.id.btnSincronizar);
        }
    }

    // 🔹 Método nuevo: permite actualizar lista sin acceder directamente a la variable
    public void actualizarLista(ArrayList<ViajeConArchivos> nuevaLista) {
        this.listaViajes.clear();
        this.listaViajes.addAll(nuevaLista);
        notifyDataSetChanged();
    }

    public void marcarSincronizado(int position) {
        if (position >= 0 && position < listaViajes.size()) {
            notifyItemChanged(position);
        }
    }

}
