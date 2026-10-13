plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.pruebas_inaoe.sensadomovil"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.pruebas_inaoe.sensadomovil"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    implementation(libs.appcompat)
    implementation(libs.material)
    implementation(libs.activity)
    implementation(libs.constraintlayout)
    implementation("androidx.cardview:cardview:1.0.0")

    // 🔹 Servicios de ubicación de Google
    implementation("com.google.android.gms:play-services-location:21.0.1")

    // 🔹 Retrofit + Gson
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    // 🔹 OkHttp
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // 🔹 PARA ARCHIVOS
    implementation("commons-io:commons-io:2.11.0")

    // 🔹 Corrutinas (opcional pero útil)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // WorkManager
    implementation("androidx.work:work-runtime:2.9.0")

    // 🔹 Testing
    implementation(libs.junit)

    // 🔹 Tests
    testImplementation(libs.junit)
    androidTestImplementation(libs.ext.junit)
    androidTestImplementation(libs.espresso.core)
}
