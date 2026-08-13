package com.filedrop.app.storage

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import java.io.IOException
import java.io.InputStream

/**
 * Transforme les URI reçues (sélecteur système ou menu Partager) en fichiers
 * décrits, sans jamais copier ni charger le contenu en mémoire.
 *
 * Point important et non contournable : une URI reçue via `ACTION_SEND` est
 * accompagnée d'une autorisation de lecture temporaire, liée à l'activité qui
 * l'a reçue. Pour que le service de transfert puisse encore lire le fichier,
 * l'autorisation doit lui être transmise en repassant les URI dans un `Intent`
 * portant `FLAG_GRANT_READ_URI_PERMISSION` (voir `FileDropService.sendIntent`).
 * Copier les fichiers dans le cache « pour être tranquille » serait la mauvaise
 * réponse : sur un envoi de plusieurs Go, cela doublerait l'espace disque et le
 * temps d'écriture.
 */
class FileResolver(context: Context) {

    private val resolver = context.applicationContext.contentResolver

    fun resolve(uri: Uri, relativePath: String = ""): SelectedFile? {
        return try {
            var name: String? = null
            var size = -1L
            resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)
                ?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                        if (nameIndex >= 0 && !cursor.isNull(nameIndex)) name = cursor.getString(nameIndex)
                        if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) size = cursor.getLong(sizeIndex)
                    }
                }

            if (size < 0) {
                // Certains fournisseurs ne renseignent pas SIZE. On retombe sur le
                // descripteur de fichier, qui donne la taille réelle.
                size = resolver.openFileDescriptor(uri, "r")?.use { it.statSize }?.takeIf { it >= 0 } ?: -1L
            }

            val resolvedName = PathSanitizer.sanitizeName(
                name ?: uri.lastPathSegment?.substringAfterLast('/') ?: "fichier",
            )
            val mimeType = resolver.getType(uri) ?: "application/octet-stream"

            if (size < 0) {
                FdLog.w(LogTags.STORAGE, "Taille inconnue pour $resolvedName : le fichier est ignoré")
                return null
            }

            FdLog.d(LogTags.STORAGE, "Fichier retenu : $resolvedName ($size o, $mimeType)")
            SelectedFile(
                uri = uri,
                displayName = resolvedName,
                relativePath = PathSanitizer.joinRelativePath(relativePath),
                size = size,
                mimeType = mimeType,
            )
        } catch (error: Exception) {
            FdLog.e(LogTags.STORAGE, "Impossible de lire les informations de $uri", error)
            null
        }
    }

    @Throws(IOException::class)
    fun openInput(uri: Uri): InputStream =
        resolver.openInputStream(uri)
            ?: throw IOException("Lecture refusée pour $uri (autorisation expirée ou fichier supprimé)")
}
