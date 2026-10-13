package com.pruebas_inaoe.sensadomovil.api;

import com.pruebas_inaoe.sensadomovil.CampaignResponse;
import com.pruebas_inaoe.sensadomovil.CreateSensedDataResponse;
import com.pruebas_inaoe.sensadomovil.SensedDataRequest;

import java.util.Map;

import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.Header;
import retrofit2.http.Multipart;
import retrofit2.http.Part;
import retrofit2.http.PartMap;
import retrofit2.http.POST;

public interface ApiService {

    //  Obtener campañas del usuario
    @POST("user/campaign/get")
    Call<CampaignResponse> getCampaigns(
            @Header("Authorization") String token
    );

    //  Crear metadatos del sensado

    @POST("user/sensed_data/create")
    Call<CreateSensedDataResponse> createSensedData(
            @Header("Authorization") String token,
            @Body SensedDataRequest body
    );


    //  servio para subir archivos de endpoim


    //  Subir archivo CSV vinculado al sensed_data_id
    @Multipart
    @POST("user/sensed_data/upload")
    Call<ResponseBody> uploadFile(
            @Header("Authorization") String token,
            @PartMap Map<String, RequestBody> params,
            @Part MultipartBody.Part file
    );

    @POST("auth/login")
    Call<ResponseBody> login(@Body RequestBody body);

}
