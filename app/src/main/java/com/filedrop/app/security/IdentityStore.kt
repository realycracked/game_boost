package com.filedrop.app.security

import android.content.Context
import android.util.Base64
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import java.util.UUID

/**
 * Conserve l'identité de l'appareil entre deux lancements.
 *
 * Limite assumée et documentée : la clé privée est stockée dans les
 * préférences privées de l'application, pas dans l'`AndroidKeyStore`. La raison
 * est concrète : l'accord de clés EC matériel (`PURPOSE_AGREE_KEY`) n'existe
 * qu'à partir d'Android 12, et FileDrop vise Android 8. Le fichier reste
 * protégé par le bac à sable de l'application ; le passage à l'`AndroidKeyStore`
 * quand il est disponible est un travail identifié pour une version ultérieure.
 */
class IdentityStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("filedrop_identity", Context.MODE_PRIVATE)

    val identity: DeviceIdentity by lazy { loadOrCreate() }

    /** Identifiant opaque, utilisé pour ne pas se découvrir soi-même. */
    val deviceId: String by lazy {
        prefs.getString(KEY_DEVICE_ID, null) ?: UUID.randomUUID().toString().take(12).also {
            prefs.edit().putString(KEY_DEVICE_ID, it).apply()
        }
    }

    private fun loadOrCreate(): DeviceIdentity {
        val storedPrivate = prefs.getString(KEY_PRIVATE, null)
        val storedPublic = prefs.getString(KEY_PUBLIC, null)
        if (storedPrivate != null && storedPublic != null) {
            try {
                val identity = DeviceIdentity.fromEncoded(
                    Base64.decode(storedPrivate, Base64.NO_WRAP),
                    Base64.decode(storedPublic, Base64.NO_WRAP),
                )
                FdLog.i(LogTags.SECURITY, "Identité chargée, empreinte ${identity.fingerprint}")
                return identity
            } catch (error: Exception) {
                FdLog.e(LogTags.SECURITY, "Identité illisible, régénération", error)
            }
        }
        val identity = DeviceIdentity.generate()
        prefs.edit()
            .putString(KEY_PRIVATE, Base64.encodeToString(identity.keyPair.private.encoded, Base64.NO_WRAP))
            .putString(KEY_PUBLIC, Base64.encodeToString(identity.publicKeyEncoded, Base64.NO_WRAP))
            .apply()
        FdLog.i(LogTags.SECURITY, "Nouvelle identité générée, empreinte ${identity.fingerprint}")
        return identity
    }

    private companion object {
        const val KEY_PRIVATE = "identity_private"
        const val KEY_PUBLIC = "identity_public"
        const val KEY_DEVICE_ID = "device_id"
    }
}
