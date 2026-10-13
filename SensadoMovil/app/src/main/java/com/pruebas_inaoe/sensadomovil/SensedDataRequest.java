package com.pruebas_inaoe.sensadomovil;

import com.google.gson.annotations.SerializedName;

public class SensedDataRequest {

    // 1. Campos privados para encapsulación
    @SerializedName("user_id")
    private int userId;

    @SerializedName("route_id")
    private String routeId;

    @SerializedName("unit_number")
    private String unitNumber;

    @SerializedName("vehicle_type_id")
    private String vehicleTypeId;

    @SerializedName("path_id")
    private int pathId; // 2. Tipo de dato corregido a int

    @SerializedName("start_timestamp")
    private String startTimestamp;

    @SerializedName("end_timestamp")
    private String endTimestamp;

    @SerializedName("campaign_uuid")
    private String campaignUuid;

    // 3. Constructor vacío (útil para Gson)
    public SensedDataRequest() {
    }

    // 4. Getters y Setters para acceder a los campos
    // (Puedes generarlos automáticamente en Android Studio:
    //  Clic derecho -> Generate -> Getter and Setter -> Seleccionar todos)

    public int getUserId() {
        return userId;
    }

    public void setUserId(int userId) {
        this.userId = userId;
    }

    public String getRouteId() {
        return routeId;
    }

    public void setRouteId(String routeId) {
        this.routeId = routeId;
    }

    public String getUnitNumber() {
        return unitNumber;
    }

    public void setUnitNumber(String unitNumber) {
        this.unitNumber = unitNumber;
    }

    public String getVehicleTypeId() {
        return vehicleTypeId;
    }

    public void setVehicleTypeId(String vehicleTypeId) {
        this.vehicleTypeId = vehicleTypeId;
    }

    public int getPathId() {
        return pathId;
    }

    public void setPathId(int pathId) {
        this.pathId = pathId;
    }

    public String getStartTimestamp() {
        return startTimestamp;
    }

    public void setStartTimestamp(String startTimestamp) {
        this.startTimestamp = startTimestamp;
    }

    public String getEndTimestamp() {
        return endTimestamp;
    }

    public void setEndTimestamp(String endTimestamp) {
        this.endTimestamp = endTimestamp;
    }

    public String getCampaignUuid() {
        return campaignUuid;
    }

    public void setCampaignUuid(String campaignUuid) {
        this.campaignUuid = campaignUuid;
    }
}
