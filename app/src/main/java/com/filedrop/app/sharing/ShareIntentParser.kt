package com.filedrop.app.sharing

import android.content.Intent
import android.net.Uri
import androidx.core.content.IntentCompat
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.storage.FileResolver
import com.filedrop.app.storage.SelectedFile

/**
 * Lit les `Intent` du menu Partager d'Android.
 *
 * Couvre `ACTION_SEND` et `ACTION_SEND_MULTIPLE`, quel que soit le type MIME
 * annoncé, et retombe sur `ClipData` quand l'application émettrice ne renseigne
 * pas `EXTRA_STREAM` — c'est fréquent, notamment depuis certains navigateurs.
 */
class ShareIntentParser(private val fileResolver: FileResolver) {

    fun parse(intent: Intent?): List<SelectedFile> {
        if (intent == null) return emptyList()

        val uris = when (intent.action) {
            Intent.ACTION_SEND -> listOfNotNull(
                IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java),
            ).ifEmpty { clipDataUris(intent) }

            Intent.ACTION_SEND_MULTIPLE ->
                IntentCompat.getParcelableArrayListExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)
                    ?.filterNotNull()
                    ?.takeIf { it.isNotEmpty() }
                    ?: clipDataUris(intent)

            else -> emptyList()
        }

        if (uris.isEmpty()) {
            val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!sharedText.isNullOrBlank()) {
                // Cas réel : partager un lien depuis un navigateur n'envoie pas de
                // fichier. FileDrop transfère des fichiers, il ne peut rien en faire.
                FdLog.w(
                    LogTags.SHARING,
                    "Partage reçu sans fichier (texte seul) : FileDrop ne transfère que des fichiers",
                )
            } else {
                FdLog.w(LogTags.SHARING, "Partage reçu (${intent.action}) sans aucune URI exploitable")
            }
            return emptyList()
        }

        val files = uris.mapNotNull { fileResolver.resolve(it) }
        FdLog.i(
            LogTags.SHARING,
            "Partage ${intent.action} : ${uris.size} URI reçues, ${files.size} fichiers exploitables " +
                "(${files.sumOf { it.size }} o au total)",
        )
        return files
    }

    private fun clipDataUris(intent: Intent): List<Uri> {
        val clipData = intent.clipData ?: return emptyList()
        return (0 until clipData.itemCount).mapNotNull { clipData.getItemAt(it)?.uri }
    }
}
