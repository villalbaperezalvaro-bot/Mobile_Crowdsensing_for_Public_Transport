package com.pruebas_inaoe.sensadomovil;

import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.pruebas_inaoe.sensadomovil.api.ApiService;
import com.pruebas_inaoe.sensadomovil.api.RetrofitClient;

import org.json.JSONObject;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Response;

public class SyncViajeWorker extends Worker {

    public static final String KEY_PATH_ID = "path_id";
    private static final String TAG = "SyncViajeWorker";

    public SyncViajeWorker(@NonNull Context context,
                           @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {

        int pathId = getInputData().getInt(KEY_PATH_ID, -1);
        Context context = getApplicationContext();
        DatabaseHelper dbHelper = new DatabaseHelper(context);

        try {
            if (pathId == -1) {
                Log.e(TAG, "No se recibió path_id");
                return Result.failure();
            }

            // ============================
            // 🔹 1. Obtener viaje
            // ============================

            ArrayList<ViajeConArchivos> viajes = dbHelper.obtenerViajesConArchivos();
            ViajeConArchivos viaje = null;

            for (ViajeConArchivos v : viajes) {
                if (v.pathId == pathId) {
                    viaje = v;
                    break;
                }
            }

            if (viaje == null) {
                String err = "Viaje con path_id " + pathId + " no encontrado en BD";
                Log.e(TAG, err);
                return Result.failure();
            }

            // ============================
            // 🔹 2. Obtener credenciales
            // ============================

            SharedPreferences prefs =
                    context.getSharedPreferences("AUTH", Context.MODE_PRIVATE);

            String token = prefs.getString("token", null);
            String email = prefs.getString("email", null);
            String password = prefs.getString("password", null);
            int userId = prefs.getInt("user_id", -1);

            if (token == null || email == null || password == null || userId == -1) {
                String err = "Credenciales incompletas en SharedPreferences";
                Log.e(TAG, err);
                registrarErrorEnTodosLosArchivos(dbHelper, viaje, err);
                return Result.failure();
            }

            ApiService api = RetrofitClient.getApiService();

            // ============================
            // 🔹 3. ENVIAR METADATOS (Solo si no tiene remote_id)
            // ============================

            int sensedDataId = viaje.sensedDataId;

            if (sensedDataId == -1) {
                SensedDataRequest request = new SensedDataRequest();
                request.setUserId(userId);
                request.setRouteId(viaje.ruta);
                request.setUnitNumber(viaje.unitId);
                request.setVehicleTypeId(viaje.vehicleTypeId);
                request.setPathId(viaje.pathId);
                request.setStartTimestamp(String.valueOf(viaje.startTimestamp));
                request.setEndTimestamp(String.valueOf(viaje.endTimestamp));
                request.setCampaignUuid(viaje.campaignUuid);

                Response<CreateSensedDataResponse> metaResponse =
                        api.createSensedData("Bearer " + token, request).execute();

                if (metaResponse.code() == 401) {
                    token = renovarToken(api, email, password);
                    metaResponse = api.createSensedData("Bearer " + token, request).execute();
                }

                if (!metaResponse.isSuccessful() || metaResponse.body() == null || !metaResponse.body().isStatus()) {
                    String errorBody = metaResponse.errorBody() != null ? metaResponse.errorBody().string() : "No error body";
                    String errorDetail = "Error creando viaje (HTTP " + metaResponse.code() + "): " + errorBody;
                    Log.e(TAG, errorDetail);
                    // Registrar el error en todos los archivos del viaje
                    for (ViajeConArchivos.ArchivoSync a : viaje.archivos) {
                        dbHelper.actualizarErrorArchivo(a.nombreArchivo, errorDetail);
                    }
                    return Result.retry();
                }

                sensedDataId = metaResponse.body().getData().getId();
                dbHelper.actualizarRemoteId(viaje.pathId, sensedDataId);
                Log.i(TAG, "Metadatos creados exitosamente. Remote ID: " + sensedDataId);
            } else {
                Log.i(TAG, "El viaje ya tiene Remote ID: " + sensedDataId + ". Saltando creación.");
            }

            // ============================
            // 🔹 4. SUBIR ARCHIVOS
            // ============================

            for (ViajeConArchivos.ArchivoSync archivo : viaje.archivos) {

                // Saltar si ya está sincronizado
                if ("Sincronizado".equals(archivo.estado)) {
                    Log.i(TAG, "Archivo ya sincronizado, saltando: " + archivo.nombreArchivo);
                    continue;
                }

                Uri fileUri = Uri.parse(archivo.nombreArchivo);
                String fileName = getFileName(context, fileUri);

                Log.d(TAG, "Subiendo archivo: " + fileName + " (URI: " + archivo.nombreArchivo + ")");

                try (InputStream inputStream = context.getContentResolver().openInputStream(fileUri)) {

                    if (inputStream == null) {
                        Log.e(TAG, "No se pudo abrir el stream para: " + fileName);
                        continue;
                    }

                    // Leer bytes del stream (necesario para Multipart)
                    byte[] bytes = okio.Okio.buffer(okio.Okio.source(inputStream)).readByteArray();

                    RequestBody fileBody = RequestBody.create(
                            bytes,
                            MediaType.parse("text/csv")
                    );

                    MultipartBody.Part filePart =
                            MultipartBody.Part.createFormData(
                                    "file",
                                    fileName,
                                    fileBody);

                    Map<String, RequestBody> params = new HashMap<>();
                    params.put("user_id", createPart(String.valueOf(userId)));
                    params.put("file_name", createPart(fileName));
                    params.put("sensed_data_id", createPart(String.valueOf(sensedDataId)));

                    Response<ResponseBody> uploadResponse =
                            api.uploadFile("Bearer " + token, params, filePart).execute();

                    if (uploadResponse.code() == 401) {
                        token = renovarToken(api, email, password);
                        uploadResponse = api.uploadFile("Bearer " + token, params, filePart).execute();
                    }

                    if (!uploadResponse.isSuccessful()) {
                        String errorBody = uploadResponse.errorBody() != null ? uploadResponse.errorBody().string() : "No error body";
                        String errorDetail = "Error subiendo archivo (HTTP " + uploadResponse.code() + "): " + errorBody;
                        Log.e(TAG, errorDetail);
                        dbHelper.actualizarErrorArchivo(archivo.nombreArchivo, errorDetail);
                        return Result.retry();
                    }

                    dbHelper.actualizarEstadoArchivo(archivo.nombreArchivo, true);
                    Log.i(TAG, "Archivo subido exitosamente: " + fileName);

                } catch (Exception e) {
                    String errorDetail = "Error fatal procesando archivo: " + e.getMessage();
                    Log.e(TAG, errorDetail, e);
                    dbHelper.actualizarErrorArchivo(archivo.nombreArchivo, errorDetail);
                    return Result.retry();
                }
            }

            Log.i(TAG, "Sincronización completa para viaje " + pathId);
            return Result.success();

        } catch (Exception e) {
            String fatalError = "Error fatal en sincronización: " + e.getMessage();
            Log.e(TAG, fatalError, e);
            // Si tenemos el pathId, intentamos registrar el error
            try {
                ArrayList<ViajeConArchivos> viajes = dbHelper.obtenerViajesConArchivos();
                for (ViajeConArchivos v : viajes) {
                    if (v.pathId == pathId) {
                        registrarErrorEnTodosLosArchivos(dbHelper, v, fatalError);
                        break;
                    }
                }
            } catch (Exception ignored) {}
            return Result.retry();
        }
    }

    private void registrarErrorEnTodosLosArchivos(DatabaseHelper dbHelper, ViajeConArchivos viaje, String error) {
        if (viaje != null && viaje.archivos != null) {
            for (ViajeConArchivos.ArchivoSync a : viaje.archivos) {
                dbHelper.actualizarErrorArchivo(a.nombreArchivo, error);
            }
        }
    }

    private String getFileName(Context context, Uri uri) {
        String result = null;
        if (uri.getScheme() != null && uri.getScheme().equals("content")) {
            Cursor cursor = context.getContentResolver().query(uri, null, null, null, null);
            try {
                if (cursor != null && cursor.moveToFirst()) {
                    int nameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME);
                    if (nameIndex != -1) {
                        result = cursor.getString(nameIndex);
                    }
                }
            } finally {
                if (cursor != null) cursor.close();
            }
        }
        if (result == null) {
            result = uri.getPath();
            if (result != null) {
                int cut = result.lastIndexOf('/');
                if (cut != -1) {
                    result = result.substring(cut + 1);
                }
            }
        }
        return result != null ? result : "unknown_file.csv";
    }

    // =============================
    // 🔐 RENOVACIÓN TOKEN REAL
    // =============================

    private String renovarToken(ApiService api,
                                String email,
                                String password) throws Exception {

        JSONObject json = new JSONObject();
        json.put("email", email);
        json.put("password", password);

        RequestBody body = RequestBody.create(
                json.toString(),
                MediaType.parse("application/json; charset=utf-8")
        );

        Response<ResponseBody> response =
                api.login(body).execute();

        if (response.isSuccessful() && response.body() != null) {

            String raw = response.body().string();
            JSONObject obj = new JSONObject(raw);

            String newToken =
                    obj.getJSONObject("data")
                            .getString("access_token");

            getApplicationContext()
                    .getSharedPreferences("AUTH", Context.MODE_PRIVATE)
                    .edit()
                    .putString("token", newToken)
                    .apply();

            Log.i(TAG, "Token renovado correctamente");

            return newToken;
        }

        Log.e(TAG, "No se pudo renovar token");
        throw new Exception("Token inválido");
    }

    private RequestBody createPart(String value) {
        return RequestBody.create(value, MultipartBody.FORM);
    }
}
