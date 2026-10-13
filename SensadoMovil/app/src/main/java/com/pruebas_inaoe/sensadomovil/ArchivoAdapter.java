package com.pruebas_inaoe.sensadomovil;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.content.FileProvider;
import androidx.recyclerview.widget.RecyclerView;

import com.pruebas_inaoe.sensadomovil.R;

import java.io.File;
import java.util.ArrayList;

public class ArchivoAdapter extends RecyclerView.Adapter<ArchivoAdapter.ArchivoViewHolder> {

    private final ArrayList<String> archivos;

    public ArchivoAdapter(ArrayList<String> archivos) {
        this.archivos = archivos;
    }

    @NonNull
    @Override
    public ArchivoViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View vista = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_archivo, parent, false);
        return new ArchivoViewHolder(vista);
    }

    @Override
    public void onBindViewHolder(@NonNull ArchivoViewHolder holder, int position) {
        String nombreArchivo = archivos.get(position);
        holder.tvNombreArchivo.setText(nombreArchivo);

        // Botón de sincronizar (si ya lo tienes)
        holder.btnSincronizar.setOnClickListener(v -> {
            Context context = v.getContext();
            Toast.makeText(context, "Sincronizando: " + nombreArchivo, Toast.LENGTH_SHORT).show();
        });

        holder.itemView.setOnClickListener(v -> {
            Context context = v.getContext();
            File archivo = new File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS + "/SensadoMovil"), nombreArchivo);

            if (archivo.exists()) {
                Uri uri;
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    uri = FileProvider.getUriForFile(context,
                            context.getPackageName() + ".provider", archivo);
                } else {
                    uri = Uri.fromFile(archivo);
                }

                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setDataAndType(uri, "text/*"); // MIME type más específico para archivos CSV
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);


                // Mostrar siempre el selector de apps (aunque ya haya una predeterminada)
                Intent chooser = Intent.createChooser(intent, "Selecciona una aplicación para abrir el archivo CSV");

                if (intent.resolveActivity(context.getPackageManager()) != null) {
                    context.startActivity(chooser);
                } else {
                    Toast.makeText(context, "No hay aplicaciones para abrir archivos CSV", Toast.LENGTH_LONG).show();
                }
            } else {
                Toast.makeText(context, "Archivo no encontrado", Toast.LENGTH_SHORT).show();
            }

        });
    }

    @Override
    public int getItemCount() {
        return archivos.size();
    }

    static class ArchivoViewHolder extends RecyclerView.ViewHolder {
        TextView tvNombreArchivo;
        Button btnSincronizar;

        public ArchivoViewHolder(@NonNull View itemView) {
            super(itemView);
            tvNombreArchivo = itemView.findViewById(R.id.tvNombreArchivo);
            btnSincronizar = itemView.findViewById(R.id.btnSincronizar);
        }
    }
}