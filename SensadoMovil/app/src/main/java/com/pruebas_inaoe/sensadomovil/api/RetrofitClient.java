package com.pruebas_inaoe.sensadomovil.api;

import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class RetrofitClient {

    private static Retrofit retrofit = null;

    public static ApiService getApiService(String baseUrl) {
        if (retrofit == null) {
            retrofit = new Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
        }
        return retrofit.create(ApiService.class);
    }

    // Opcional: sobrecarga que usa tu base URL fija
    public static ApiService getApiService() {
        return getApiService("https://hu-api.rutamovil.com.mx/api/");
    }

    public static ApiService getDefaultApi() {
        return getApiService("https://hu-api.rutamovil.com.mx/api/");
    }

}
