import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

// --- Signature release (facultative) -----------------------------------------
// La V1 se construit en debug et n'a besoin d'aucun secret.
// Pour produire plus tard un APK release signé, il suffit de fournir soit un
// fichier keystore.properties à la racine, soit les variables d'environnement
// FILEDROP_KEYSTORE / FILEDROP_KEYSTORE_PASSWORD / FILEDROP_KEY_ALIAS /
// FILEDROP_KEY_PASSWORD (voir README, section « APK release signé »).
// Sans ces valeurs, la configuration de signature n'est simplement pas créée.
val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.exists()) {
        keystorePropertiesFile.inputStream().use { load(it) }
    }
}

fun signingValue(propertyKey: String, envKey: String): String? =
    keystoreProperties.getProperty(propertyKey) ?: System.getenv(envKey)

val releaseStoreFile = signingValue("storeFile", "FILEDROP_KEYSTORE")
val releaseStorePassword = signingValue("storePassword", "FILEDROP_KEYSTORE_PASSWORD")
val releaseKeyAlias = signingValue("keyAlias", "FILEDROP_KEY_ALIAS")
val releaseKeyPassword = signingValue("keyPassword", "FILEDROP_KEY_PASSWORD")
val hasReleaseSigning = listOf(
    releaseStoreFile,
    releaseStorePassword,
    releaseKeyAlias,
    releaseKeyPassword,
).all { !it.isNullOrBlank() }

android {
    namespace = "com.filedrop.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.filedrop.app"
        // Android 8.0. En dessous, les canaux de notification et les services
        // de premier plan modernes n'existent pas : la V1 ne les émule pas.
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    if (hasReleaseSigning) {
        signingConfigs {
            create("release") {
                storeFile = file(releaseStoreFile!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        debug {
            // Suffixe distinct : l'APK debug peut cohabiter avec une future
            // version release sur le même téléphone.
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    testOptions {
        unitTests {
            // Les classes du framework Android (android.util.Log en particulier)
            // ne sont pas implémentées dans les tests JVM. Sans cela, chaque appel
            // de journalisation ferait échouer un test qui ne teste pas les logs.
            isReturnDefaultValues = true
        }
    }

    lint {
        // Un warning ne doit jamais bloquer un build lancé depuis un téléphone.
        abortOnError = false
        checkReleaseBuilds = false
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(libs.kotlinx.coroutines.android)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    debugImplementation(libs.androidx.compose.ui.tooling)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}
