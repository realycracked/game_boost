// Racine du projet FileDrop.
// Les plugins sont déclarés ici sans être appliqués : chaque module les applique
// via le catalogue de versions (gradle/libs.versions.toml).
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
}
