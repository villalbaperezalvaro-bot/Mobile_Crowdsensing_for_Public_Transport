package com.pruebas_inaoe.sensadomovil;

import java.util.ArrayList;

public class ViajeConArchivos {

    // 🔹 Ambos campos: el path_id (local) y el sensedDataId (remoto)
    public int sensedDataId;     // ID devuelto por /sensed_data/create
    public int pathId;           // ID interno local (SQLite)
    public String ruta;          // ID de la ruta (numérico para el servidor)
    public String rutaNombre;    // Nombre legible (ej: "Ruta Chipilo")
    public String campaignUuid;  // UUID de la campaña (para el servidor)
    public String campaniaNombre; // Nombre legible de la campaña
    public String unitId;
    public String vehicleTypeId;
    public long startTimestamp;
    public long endTimestamp;
    public ArrayList<ArchivoSync> archivos;

    // Constructor completo
    public ViajeConArchivos(int sensedDataId, int pathId, String ruta, String rutaNombre, String campaignUuid, String campaniaNombre, String unitId, String vehicleTypeId, long startTimestamp, long endTimestamp, ArrayList<ArchivoSync> archivos) {
        this.sensedDataId = sensedDataId;
        this.pathId = pathId;
        this.ruta = ruta;
        this.rutaNombre = rutaNombre;
        this.campaignUuid = campaignUuid;
        this.campaniaNombre = campaniaNombre;
        this.unitId = unitId;
        this.vehicleTypeId = vehicleTypeId;
        this.startTimestamp = startTimestamp;
        this.endTimestamp = endTimestamp;
        this.archivos = archivos;
    }

    // Constructor simplificado para compatibilidad o creación rápida
    public ViajeConArchivos(int pathId, String ruta, String campaignUuid, String unitId, String vehicleTypeId, long startTimestamp, long endTimestamp, ArrayList<ArchivoSync> archivos) {
        this(-1, pathId, ruta, ruta, campaignUuid, campaignUuid, unitId, vehicleTypeId, startTimestamp, endTimestamp, archivos);
    }

    public static class ArchivoSync {
        public String nombreArchivo;
        public String estado;
        public String errorMsg;

        public ArchivoSync(String nombreArchivo, String estado) {
            this(nombreArchivo, estado, null);
        }

        public ArchivoSync(String nombreArchivo, String estado, String errorMsg) {
            this.nombreArchivo = nombreArchivo;
            this.estado = estado;
            this.errorMsg = errorMsg;
        }
    }
}
