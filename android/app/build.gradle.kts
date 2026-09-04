import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseApiBaseUrl = providers.gradleProperty("releaseApiBaseUrl").orNull
val releaseStoreFile = providers.environmentVariable("LEARN_SMART_RELEASE_STORE_FILE").orNull
val releaseStorePassword = providers.environmentVariable("LEARN_SMART_RELEASE_STORE_PASSWORD").orNull
val releaseKeyAlias = providers.environmentVariable("LEARN_SMART_RELEASE_KEY_ALIAS").orNull
val releaseKeyPassword = providers.environmentVariable("LEARN_SMART_RELEASE_KEY_PASSWORD").orNull
// Public OAuth audience, never an OpenAI key or OAuth client secret.
val googleServerClientId = providers.gradleProperty("googleServerClientId").orNull.orEmpty().trim()
require(googleServerClientId.isEmpty() || Regex("[0-9]+-[A-Za-z0-9_-]+\\.apps\\.googleusercontent\\.com").matches(googleServerClientId)) {
    "googleServerClientId must be a Google web OAuth client ID, or omitted to disable Google sign-in"
}
val validateReleaseEndpoint = tasks.register("validateReleaseEndpoint") {
    doLast {
        val raw = releaseApiBaseUrl ?: error("Release requires -PreleaseApiBaseUrl=https://your-confirmed-backend. No production target is configured.")
        val uri = runCatching { URI(raw) }.getOrElse { error("Release API URL is invalid") }
        require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null && uri.query == null && uri.fragment == null) {
            "Release API URL must use HTTPS with a host and no credentials, query or fragment"
        }
        val host = uri.host.lowercase().trimEnd('.')
        require(host !in setOf("localhost", "10.0.2.2", "::1", "[::1]") && !host.startsWith("127.") && (uri.port == -1 || uri.port in 1..65535)) {
            "Release API URL cannot target the local emulator backend"
        }
    }
}
val validateReleaseSigning = tasks.register("validateReleaseSigning") {
    doLast {
        val values = mapOf(
            "LEARN_SMART_RELEASE_STORE_FILE" to releaseStoreFile,
            "LEARN_SMART_RELEASE_STORE_PASSWORD" to releaseStorePassword,
            "LEARN_SMART_RELEASE_KEY_ALIAS" to releaseKeyAlias,
            "LEARN_SMART_RELEASE_KEY_PASSWORD" to releaseKeyPassword,
        )
        val missing = values.filterValues { it.isNullOrBlank() }.keys
        require(missing.isEmpty()) { "Release signing environment is incomplete: ${missing.joinToString()}" }
        val keyStore = file(releaseStoreFile!!)
        require(keyStore.isFile) { "Release keystore does not exist or is not a file" }
    }
}
tasks.configureEach {
    if (name == "preReleaseBuild") dependsOn(validateReleaseEndpoint, validateReleaseSigning)
}

android {
    namespace = "com.konetibalaji.learning"
    compileSdk = 37

    signingConfigs {
        create("privateRelease") {
            if (!releaseStoreFile.isNullOrBlank() && !releaseStorePassword.isNullOrBlank() &&
                !releaseKeyAlias.isNullOrBlank() && !releaseKeyPassword.isNullOrBlank()) {
                storeFile = file(releaseStoreFile)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    defaultConfig {
        applicationId = "com.konetibalaji.learning"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.1.0"
        buildConfigField("String", "GOOGLE_SERVER_CLIENT_ID", "\"$googleServerClientId\"")
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000\"")
            manifestPlaceholders["cleartextAllowed"] = "true"
        }
        release {
            val endpoint = releaseApiBaseUrl.orEmpty().trimEnd('/').replace("\\", "\\\\").replace("\"", "\\\"")
            buildConfigField("String", "API_BASE_URL", "\"$endpoint\"")
            manifestPlaceholders["cleartextAllowed"] = "false"
            signingConfig = signingConfigs.getByName("privateRelease")
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.06.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.6.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.2.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    testImplementation("junit:junit:4.13.2")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
