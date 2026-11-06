import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseSigning = listOf(
    "SARAS_KEYSTORE_PATH", "SARAS_KEYSTORE_PASSWORD", "SARAS_KEY_ALIAS", "SARAS_KEY_PASSWORD"
).associateWith { providers.environmentVariable(it).orNull }
val signingRequested = releaseSigning.values.any { !it.isNullOrBlank() }
val studyServerUrl = providers.gradleProperty("sarasServerUrl").orNull?.trim()?.trimEnd('/').orEmpty()
if (studyServerUrl.isNotEmpty()) {
    val uri = URI(studyServerUrl)
    require(uri.scheme == "https" && uri.host != null && uri.userInfo == null &&
        uri.rawPath.isEmpty() && uri.rawQuery == null && uri.rawFragment == null) {
        "sarasServerUrl must be an HTTPS origin."
    }
}
if (signingRequested) {
    require(releaseSigning.values.all { !it.isNullOrBlank() }) { "Supply all four Saras signing variables." }
}

android {
    namespace = "com.studycompanion"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.studycompanion"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "STUDY_SERVER_URL", "\"$studyServerUrl\"")
    }
    if (providers.gradleProperty("sarasQaInstall").orNull == "true") {
        buildTypes.getByName("debug").applicationIdSuffix = ".qa"
    }
    if (signingRequested) {
        signingConfigs.create("release") {
            storeFile = file(releaseSigning.getValue("SARAS_KEYSTORE_PATH")!!)
            storePassword = releaseSigning.getValue("SARAS_KEYSTORE_PASSWORD")
            keyAlias = releaseSigning.getValue("SARAS_KEY_ALIAS")
            keyPassword = releaseSigning.getValue("SARAS_KEY_PASSWORD")
        }
        buildTypes.getByName("release").signingConfig = signingConfigs.getByName("release")
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2025.04.01"))
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.6.0")
    // googleid 1.2.1 requires newer Kotlin metadata than this build supports.
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.room:room-runtime:2.7.1")
    annotationProcessor("androidx.room:room-compiler:2.7.1")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation(platform("androidx.compose:compose-bom:2025.04.01"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
