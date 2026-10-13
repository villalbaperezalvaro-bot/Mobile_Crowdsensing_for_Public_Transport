package com.pruebas_inaoe.sensadomovil;

import com.google.gson.annotations.SerializedName;

public class CreateSensedDataResponse {

    @SerializedName("status")
    private boolean status; // Campo privado

    @SerializedName("data")
    private Data data; // Campo privado

    // --- GETTERS ---
    // Este método soluciona el error "Cannot resolve method 'isStatus'"
    public boolean isStatus() {
        return status;
    }

    // Este método soluciona el error "Cannot resolve method 'getData'"
    public Data getData() {
        return data;
    }

    // --- CLASE INTERNA PARA EL OBJETO 'data' ---
    public static class Data {
        @SerializedName("id")
        private int id; // Campo privado

        // Getter para acceder al id
        public int getId() {
            return id;
        }
    }
}
