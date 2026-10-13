package com.pruebas_inaoe.sensadomovil;

import static android.content.ContentValues.TAG;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteException;
import android.database.sqlite.SQLiteOpenHelper;
import android.provider.BaseColumns;
import android.util.Log;

import java.util.ArrayList;

// Clase Contract para definir el esquema de la tabla
final class MetadatosContract {
    private MetadatosContract() {}

    /* Clase interna que define el contenido de la tabla de Metadatos del sensado */
    public static class SesionEntry implements BaseColumns {
        public static final String TABLE_NAME = "trip_data_table";
        public static final String COLUMN_PATH_ID = "path_id";
        public static final String COLUMN_USER_ID = "user_id";
        public static final String COLUMN_ROUTE_NAME = "route_id"; // ID de la ruta (numérico)
        public static final String COLUMN_ROUTE_DISPLAY_NAME = "route_display_name"; // Nombre de la ruta (texto)
        public static final String COLUMN_START_TIMESTAMP = "start_timestamp";
        public static final String COLUMN_END_TIMESTAMP = "end_timestamp";
        public static final String COLUMN_TRANSPORT_TYPE = "vehicle_type_id";
        public static final String COLUMN_UNIT_NUMBER = "unit_id";
        public static final String COLUMN_REMOTE_ID = "remote_id"; // ID del servidor

        /// 👇 Agregada aquí la nueva columna miercoles 22 de octubre
        public static final String COLUMN_CAMPAIGN_NAME = "campaign_name"; // Nombre de la campaña
        public static final String COLUMN_CAMPAIGN_ID = "campaign_id";
        public static final String COLUMN_CAMPAIGN_UUID = "campaign_uuid";

    }
    // Nueva tabla para los archivos asociados a una sesión
    public static class SessionFileEntry implements BaseColumns {
        public static final String TABLE_NAME = "file_table";

        public static final String COLUMN_SESSION_ID_FK = "trip_data_fk"; // Clave foránea a trip date table
        public static final String COLUMN_FILE_TYPE = "file_type"; // Ej: "gps", "acel", "giro"
        public static final String COLUMN_IS_SYNCED = "is_synced"; // columna para marcar el estado de sincronización
        public static final String COLUMN_ERROR_MSG = "error_msg"; // Mensaje de error de sincronización

        public static final String COLUMN_FILE_NAME = "file_name";
    }
    // Nueva tabla para usuarios
    public static class UserEntry implements BaseColumns {
        public static final String TABLE_NAME = "users_table";
        public static final String COLUMN_USER_ID = "user_id";
        public static final String COLUMN_NAME = "user_name";
        public static final String COLUMN_EMAIL = "email";
        public static final String COLUMN_REGISTER_DATE = "register_date";

    }

    // 👇 Agregada aquí la nueva tabla miercoles 23 de octubre
    public static class CampaignEntry implements BaseColumns {
        public static final String TABLE_NAME = "campaigns_table";
        public static final String COLUMN_CAMPAIGN_UUID = "campaign_uuid"; // ahora viene del backend
        // viene del backend
        public static final String COLUMN_CAMPAIGN_NAME = "campaign_name";
        public static final String COLUMN_DESCRIPTION = "description"; // opcional
    }

}

public class DatabaseHelper extends SQLiteOpenHelper {
    public static final int DATABASE_VERSION = 14;
    public static final String DATABASE_NAME = "Sensado.db";

    // SQL para crear la tabla de sesiones
    private static final String SQL_CREATE_SESSIONS_TABLE =
            "CREATE TABLE " + MetadatosContract.SesionEntry.TABLE_NAME + " (" +
                    MetadatosContract.SesionEntry._ID + " INTEGER PRIMARY KEY AUTOINCREMENT," +
                    MetadatosContract.SesionEntry.COLUMN_PATH_ID + " INTEGER UNIQUE," +
                    MetadatosContract.SesionEntry.COLUMN_USER_ID + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_ROUTE_NAME + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_UNIT_NUMBER + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_TRANSPORT_TYPE + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_UUID + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME + " TEXT," +
                    MetadatosContract.SesionEntry.COLUMN_REMOTE_ID + " INTEGER DEFAULT -1," +
                    MetadatosContract.SesionEntry.COLUMN_START_TIMESTAMP + " INTEGER," +
                    MetadatosContract.SesionEntry.COLUMN_END_TIMESTAMP + " INTEGER)";
    






    // SQL para crear la tabla de archivos de sesión
    private static final String SQL_CREATE_SESSION_FILES_TABLE =
            "CREATE TABLE " + MetadatosContract.SessionFileEntry.TABLE_NAME + " (" +
                    MetadatosContract.SessionFileEntry._ID + " INTEGER PRIMARY KEY AUTOINCREMENT," +
                    MetadatosContract.SessionFileEntry.COLUMN_SESSION_ID_FK + " INTEGER NOT NULL," +
                    MetadatosContract.SessionFileEntry.COLUMN_FILE_TYPE + " TEXT NOT NULL," + // ej. "gps", "acel"
                    MetadatosContract.SessionFileEntry.COLUMN_FILE_NAME + " TEXT," +
                    MetadatosContract.SessionFileEntry.COLUMN_IS_SYNCED + " INTEGER DEFAULT 0," + // 0 = no sincronizado, 1 = sincronizado
                    MetadatosContract.SessionFileEntry.COLUMN_ERROR_MSG + " TEXT," +
                    "FOREIGN KEY (" + MetadatosContract.SessionFileEntry.COLUMN_SESSION_ID_FK + ") " +
                    "REFERENCES " + MetadatosContract.SesionEntry.TABLE_NAME + "(" + MetadatosContract.SesionEntry._ID + ") " +
                    "ON DELETE CASCADE)"; // Se agrega para poder eliminar en cascada

    // SQL para crear la tabla de usuarios
    private static final String SQL_CREATE_USERS_TABLE =
            "CREATE TABLE " + MetadatosContract.UserEntry.TABLE_NAME + " (" +
                    MetadatosContract.UserEntry._ID + " INTEGER PRIMARY KEY AUTOINCREMENT," +
                    MetadatosContract.UserEntry.COLUMN_USER_ID + " INTEGER UNIQUE," +
                    MetadatosContract.UserEntry.COLUMN_NAME + " TEXT," +
                    MetadatosContract.UserEntry.COLUMN_EMAIL + " TEXT," +
                    MetadatosContract.UserEntry.COLUMN_REGISTER_DATE + " INTEGER)";
//
// 👇 Agregada aquí la nueva tabla miercoles 23 de octubre
private static final String SQL_CREATE_CAMPAIGNS_TABLE =
        "CREATE TABLE " + MetadatosContract.CampaignEntry.TABLE_NAME + " (" +
                MetadatosContract.CampaignEntry._ID + " INTEGER PRIMARY KEY AUTOINCREMENT," +
                MetadatosContract.CampaignEntry.COLUMN_CAMPAIGN_UUID + " TEXT UNIQUE," +
                MetadatosContract.CampaignEntry.COLUMN_CAMPAIGN_NAME + " TEXT NOT NULL," +
                MetadatosContract.CampaignEntry.COLUMN_DESCRIPTION + " TEXT)";



    private static final String SQL_DELETE_SESSIONS_TABLE =
            "DROP TABLE IF EXISTS " + MetadatosContract.SesionEntry.TABLE_NAME;
    private static final String SQL_DELETE_SESSION_FILES_TABLE =
            "DROP TABLE IF EXISTS " + MetadatosContract.SessionFileEntry.TABLE_NAME;

    public DatabaseHelper(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL(SQL_CREATE_SESSIONS_TABLE);
        db.execSQL(SQL_CREATE_SESSION_FILES_TABLE);
        db.execSQL(SQL_CREATE_USERS_TABLE);
        // Habilitar claves foráneas
        db.execSQL("PRAGMA foreign_keys=ON;");
// 👇 Agregada aquí la nueva tabla miercoles 23 de octubre
        db.execSQL(SQL_CREATE_CAMPAIGNS_TABLE);

    }
    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        try {
            db.beginTransaction();

            // Migraciones anteriores preservadas
            if (oldVersion < 11) {
                if (tableExists(db, MetadatosContract.SessionFileEntry.TABLE_NAME) &&
                        !columnExists(db, MetadatosContract.SessionFileEntry.TABLE_NAME,
                                MetadatosContract.SessionFileEntry.COLUMN_IS_SYNCED)) {
                    db.execSQL("ALTER TABLE " + MetadatosContract.SessionFileEntry.TABLE_NAME +
                            " ADD COLUMN " + MetadatosContract.SessionFileEntry.COLUMN_IS_SYNCED +
                            " INTEGER DEFAULT 0");
                }
                if (!tableExists(db, MetadatosContract.UserEntry.TABLE_NAME)) {
                    db.execSQL(SQL_CREATE_USERS_TABLE);
                }
                if (!tableExists(db, MetadatosContract.CampaignEntry.TABLE_NAME)) {
                    db.execSQL(SQL_CREATE_CAMPAIGNS_TABLE);
                }
            }

            if (oldVersion < 12) {
                if (!columnExists(db, MetadatosContract.SesionEntry.TABLE_NAME,
                        MetadatosContract.SesionEntry.COLUMN_REMOTE_ID)) {
                    db.execSQL("ALTER TABLE " + MetadatosContract.SesionEntry.TABLE_NAME +
                            " ADD COLUMN " + MetadatosContract.SesionEntry.COLUMN_REMOTE_ID +
                            " INTEGER DEFAULT -1");
                }
            }

            // Migración a versión 13: Añadir columna de error
            if (oldVersion < 13) {
                if (!columnExists(db, MetadatosContract.SessionFileEntry.TABLE_NAME,
                        MetadatosContract.SessionFileEntry.COLUMN_ERROR_MSG)) {
                    db.execSQL("ALTER TABLE " + MetadatosContract.SessionFileEntry.TABLE_NAME +
                            " ADD COLUMN " + MetadatosContract.SessionFileEntry.COLUMN_ERROR_MSG +
                            " TEXT");
                }
            }

            // Migración V14: Añadir nombres de pantalla
            if (oldVersion < 14) {
                if (!columnExists(db, MetadatosContract.SesionEntry.TABLE_NAME,
                        MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME)) {
                    db.execSQL("ALTER TABLE " + MetadatosContract.SesionEntry.TABLE_NAME +
                            " ADD COLUMN " + MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME +
                            " TEXT");
                }
                if (!columnExists(db, MetadatosContract.SesionEntry.TABLE_NAME,
                        MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME)) {
                    db.execSQL("ALTER TABLE " + MetadatosContract.SesionEntry.TABLE_NAME +
                            " ADD COLUMN " + MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME +
                            " TEXT");
                }
            }

            db.setTransactionSuccessful();
        } catch (SQLiteException e) {
            Log.e(TAG, "Error durante la migración de la base de datos", e);
        } finally {
            db.endTransaction();
        }
    }

    // Métodos auxiliares
    private boolean tableExists(SQLiteDatabase db, String tableName) {
        Cursor cursor = db.rawQuery(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                new String[]{tableName});
        boolean exists = cursor.getCount() > 0;
        cursor.close();
        return exists;
    }

    private boolean columnExists(SQLiteDatabase db, String tableName, String columnName) {
        Cursor cursor = null;
        try {
            cursor = db.rawQuery("PRAGMA table_info(" + tableName + ")", null);
            if (cursor != null) {
                while (cursor.moveToNext()) {
                    String name = cursor.getString(cursor.getColumnIndexOrThrow("name"));
                    if (columnName.equals(name)) {
                        return true;
                    }
                }
            }
            return false;
        } finally {
            if (cursor != null) cursor.close();
        }
    }

    @Override
    public void onDowngrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        onUpgrade(db, oldVersion, newVersion);
    }

    public int getNextPath_id(SQLiteDatabase readableDb) { // Pasar la instancia de BD
        Cursor cursor = null;
        int maxId = 0;
        try {
            cursor = readableDb.query(
                    MetadatosContract.SesionEntry.TABLE_NAME,
                    new String[]{"MAX(" + MetadatosContract.SesionEntry.COLUMN_PATH_ID + ")"},
                    null,
                    null,
                    null,
                    null,
                    null
            );
            if (cursor != null && cursor.moveToFirst()) {
                maxId = cursor.getInt(0); // Obtiene el valor MAX
            }
        } catch (Exception e) {
            Log.e(TAG, "Fallo al recuperar el path_id");
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
        return maxId + 1; // Devuelve el siguiente ID disponible
    }

    public ArrayList<ViajeConArchivos> obtenerViajesConArchivos() {
        ArrayList<ViajeConArchivos> lista = new ArrayList<>();
        SQLiteDatabase db = this.getReadableDatabase();

        String query = "SELECT ses." + MetadatosContract.SesionEntry.COLUMN_PATH_ID + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_ROUTE_NAME + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_ROUTE_DISPLAY_NAME + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_UUID + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_CAMPAIGN_NAME + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_UNIT_NUMBER + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_TRANSPORT_TYPE + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_START_TIMESTAMP + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_END_TIMESTAMP + ", " +
                "ses." + MetadatosContract.SesionEntry.COLUMN_REMOTE_ID + ", " +
                "arch." + MetadatosContract.SessionFileEntry.COLUMN_FILE_NAME + ", " +
                "arch." + MetadatosContract.SessionFileEntry.COLUMN_IS_SYNCED + ", " +
                "arch." + MetadatosContract.SessionFileEntry.COLUMN_ERROR_MSG + " " +
                "FROM " + MetadatosContract.SesionEntry.TABLE_NAME + " ses " +
                "JOIN " + MetadatosContract.SessionFileEntry.TABLE_NAME + " arch " +
                "ON ses." + MetadatosContract.SesionEntry._ID + " = arch." + MetadatosContract.SessionFileEntry.COLUMN_SESSION_ID_FK + " " +
                "ORDER BY ses." + MetadatosContract.SesionEntry.COLUMN_PATH_ID + " DESC";

        Cursor cursor = db.rawQuery(query, null);

        int lastPathId = -1;
        String lastRutaId = "";
        String lastRutaNombre = "";
        String lastCampaignUuid = null;
        String lastCampaniaNombre = "";
        String lastUnitId = "";
        String lastVehicleTypeId = "";
        long lastStart = 0;
        long lastEnd = 0;
        int lastRemoteId = -1;
        ArrayList<ViajeConArchivos.ArchivoSync> archivosActuales = new ArrayList<>();

        if (cursor.moveToFirst()) {
            do {
                int pathId = cursor.getInt(0);
                String rutaId = cursor.getString(1);
                String rutaNombre = cursor.getString(2);
                String campaignUuid = cursor.getString(3);
                String campaniaNombre = cursor.getString(4);
                String unitId = cursor.getString(5);
                String vehicleTypeId = cursor.getString(6);
                long start = cursor.getLong(7);
                long end = cursor.getLong(8);
                int remoteId = cursor.getInt(9);
                String archivo = cursor.getString(10);
                int isSynced = cursor.getInt(11);
                String errorMsg = cursor.getString(12);

                String estado = (isSynced == 1) ? "Sincronizado" : "Pendiente";

                if (pathId != lastPathId && lastPathId != -1) {
                    lista.add(new ViajeConArchivos(lastRemoteId, lastPathId, lastRutaId, lastRutaNombre, lastCampaignUuid, lastCampaniaNombre, lastUnitId, lastVehicleTypeId, lastStart, lastEnd, new ArrayList<>(archivosActuales)));
                    archivosActuales.clear();
                }

                lastPathId = pathId;
                lastRutaId = rutaId;
                // Si el nombre guardado es nulo o vacío, usamos el ID como fallback
                lastRutaNombre = (rutaNombre != null && !rutaNombre.trim().isEmpty()) ? rutaNombre : ("Ruta " + rutaId);
                
                lastCampaignUuid = campaignUuid;
                // Si el nombre de campaña está vacío, usamos una etiqueta descriptiva
                lastCampaniaNombre = (campaniaNombre != null && !campaniaNombre.trim().isEmpty()) ? campaniaNombre : ("Campaña ID: " + (campaignUuid != null ? campaignUuid : "Desconocida"));
                
                lastUnitId = unitId;
                lastVehicleTypeId = vehicleTypeId;
                lastStart = start;
                lastEnd = end;
                lastRemoteId = remoteId;
                archivosActuales.add(new ViajeConArchivos.ArchivoSync(archivo, estado, errorMsg));
            } while (cursor.moveToNext());

            if (!archivosActuales.isEmpty()) {
                lista.add(new ViajeConArchivos(lastRemoteId, lastPathId, lastRutaId, lastRutaNombre, lastCampaignUuid, lastCampaniaNombre, lastUnitId, lastVehicleTypeId, lastStart, lastEnd, archivosActuales));
            }
        }

        cursor.close();
        return lista;
    }



    public void actualizarEstadoArchivo(String nombreArchivo, boolean sincronizado) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put(MetadatosContract.SessionFileEntry.COLUMN_IS_SYNCED, sincronizado ? 1 : 0);
        if (sincronizado) {
            values.putNull(MetadatosContract.SessionFileEntry.COLUMN_ERROR_MSG);
        }

        int rows = db.update(
                MetadatosContract.SessionFileEntry.TABLE_NAME,
                values,
                MetadatosContract.SessionFileEntry.COLUMN_FILE_NAME + " = ?",
                new String[]{nombreArchivo}
        );

        Log.d(TAG, "Archivo actualizado: " + nombreArchivo + ", filas afectadas: " + rows);
    }

    public void actualizarErrorArchivo(String nombreArchivo, String errorMsg) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put(MetadatosContract.SessionFileEntry.COLUMN_ERROR_MSG, errorMsg);

        db.update(
                MetadatosContract.SessionFileEntry.TABLE_NAME,
                values,
                MetadatosContract.SessionFileEntry.COLUMN_FILE_NAME + " = ?",
                new String[]{nombreArchivo}
        );
    }

    public void actualizarRemoteId(int pathId, int remoteId) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put(MetadatosContract.SesionEntry.COLUMN_REMOTE_ID, remoteId);

        db.update(MetadatosContract.SesionEntry.TABLE_NAME,
                values,
                MetadatosContract.SesionEntry.COLUMN_PATH_ID + " = ?",
                new String[]{String.valueOf(pathId)});
    }

    /**
     * Guarda o actualiza un usuario en la base de datos
     */
    public long saveOrUpdateUser(int userId, String userName, String email) {
        SQLiteDatabase db = this.getWritableDatabase();
        ContentValues values = new ContentValues();

        values.put(MetadatosContract.UserEntry.COLUMN_USER_ID, userId);
        values.put(MetadatosContract.UserEntry.COLUMN_NAME, userName);
        values.put(MetadatosContract.UserEntry.COLUMN_EMAIL, email);
        values.put(MetadatosContract.UserEntry.COLUMN_REGISTER_DATE, System.currentTimeMillis());

        try {
            // Usamos INSERT OR REPLACE para actualizar si ya existe
            return db.insertWithOnConflict(
                    MetadatosContract.UserEntry.TABLE_NAME,
                    null,
                    values,
                    SQLiteDatabase.CONFLICT_REPLACE);
        } catch (Exception e) {
            Log.e(TAG, "Error al guardar usuario", e);
            return -1;
        } finally {
            db.close();
        }
    }

    /**
     * Obtiene el ID del último usuario registrado
     */
    public int getLastUserId() {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.query(
                    MetadatosContract.UserEntry.TABLE_NAME,
                    new String[]{MetadatosContract.UserEntry.COLUMN_USER_ID},
                    null, null, null, null,
                    MetadatosContract.UserEntry.COLUMN_REGISTER_DATE + " DESC",
                    "1");

            if (cursor != null && cursor.moveToFirst()) {
                return cursor.getInt(cursor.getColumnIndexOrThrow(MetadatosContract.UserEntry.COLUMN_USER_ID));
            }
        } catch (Exception e) {
            Log.e(TAG, "Error al obtener user_id", e);
        } finally {
            if (cursor != null) cursor.close();
            db.close();
        }
        return -1; // Valor por defecto si no se encuentra
    }

    /**
     * Obtiene toda la información del usuario actual
     */
    public UserInfo getCurrentUserInfo() {
        SQLiteDatabase db = this.getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.query(
                    MetadatosContract.UserEntry.TABLE_NAME,
                    new String[]{
                            MetadatosContract.UserEntry.COLUMN_USER_ID,
                            MetadatosContract.UserEntry.COLUMN_NAME,
                            MetadatosContract.UserEntry.COLUMN_EMAIL
                    },
                    null, null, null, null,
                    MetadatosContract.UserEntry.COLUMN_REGISTER_DATE + " DESC",
                    "1");

            if (cursor != null && cursor.moveToFirst()) {
                return new UserInfo(
                        cursor.getInt(cursor.getColumnIndexOrThrow(MetadatosContract.UserEntry.COLUMN_USER_ID)),
                        cursor.getString(cursor.getColumnIndexOrThrow(MetadatosContract.UserEntry.COLUMN_NAME)),
                        cursor.getString(cursor.getColumnIndexOrThrow(MetadatosContract.UserEntry.COLUMN_EMAIL))
                );
            }
        } catch (Exception e) {
            Log.e(TAG, "Error al obtener información del usuario", e);
        } finally {
            if (cursor != null) cursor.close();
            db.close();
        }
        return null;
    }

    // Clase para contener la información del usuario
    public static class UserInfo {
        public final int userId;
        public final String userName;
        public final String email;

        public UserInfo(int userId, String userName, String email) {
            this.userId = userId;
            this.userName = userName;
            this.email = email;
        }
    }



    // Opcional: Habilitar claves foráneas cada vez que se abre la base de datos si es necesario
    @Override
    public void onOpen(SQLiteDatabase db) {
        super.onOpen(db);
        if (!db.isReadOnly()) {
            // Habilitar
            // claves foráneas
            db.execSQL("PRAGMA foreign_keys=ON;");
        }
    }
}