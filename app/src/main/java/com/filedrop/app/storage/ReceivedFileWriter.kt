package com.filedrop.app.storage

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.DocumentsContract
import android.provider.MediaStore
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.transfer.protocol.FileMeta
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.OutputStream

/**
 * Écrit les fichiers reçus, en respectant le stockage cloisonné d'Android.
 *
 * Trois stratégies, dans l'ordre :
 *
 *  1. **dossier choisi par l'utilisateur** (URI d'arborescence obtenue via le
 *     sélecteur système). C'est le seul moyen officiel d'écrire ailleurs que
 *     dans les dossiers publics ;
 *  2. **`MediaStore`, dossier `Download/FileDrop`** (Android 10+). Aucune
 *     permission requise, et les fichiers apparaissent immédiatement dans
 *     l'application Fichiers et dans la galerie pour les médias ;
 *  3. **dossier public `Download/FileDrop`** (Android 8 et 9), qui exige
 *     `WRITE_EXTERNAL_STORAGE` ; si elle n'est pas accordée, repli sur le
 *     dossier privé de l'application, qui reste accessible depuis l'app.
 *
 * L'arborescence annoncée par l'émetteur est reproduite dans tous les cas.
 */
class ReceivedFileWriter(
    context: Context,
    private val settings: SettingsStore,
) {

    private val appContext = context.applicationContext
    private val resolver = appContext.contentResolver

    /** Cible ouverte : le flux est écrit par morceaux, jamais tamponné en entier. */
    class Target(
        val output: OutputStream,
        val location: String,
        private val onFinish: () -> Unit,
        private val onAbort: () -> Unit,
    ) {
        fun finish() {
            runCatching { output.flush() }
            runCatching { output.close() }
            onFinish()
        }

        fun abort() {
            runCatching { output.close() }
            onAbort()
        }
    }

    @Throws(IOException::class)
    fun open(meta: FileMeta): Target {
        val name = PathSanitizer.sanitizeName(meta.name)
        val segments = PathSanitizer.sanitizeRelativePath(meta.relativePath)
        val mimeType = meta.mimeType.ifBlank { "application/octet-stream" }

        settings.destinationTreeUri.value?.let { tree ->
            runCatching { openInTree(Uri.parse(tree), segments, name, mimeType) }
                .onSuccess { return it }
                .onFailure {
                    FdLog.w(
                        LogTags.STORAGE,
                        "Dossier de destination choisi inutilisable, repli sur le dossier par défaut",
                        it,
                    )
                }
        }

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            openInMediaStore(segments, name, mimeType)
        } else {
            openLegacyFile(segments, name)
        }
    }

    // --- 1. Dossier choisi par l'utilisateur (SAF) ---------------------------

    private fun openInTree(treeUri: Uri, segments: List<String>, name: String, mimeType: String): Target {
        var parent = DocumentsContract.buildDocumentUriUsingTree(
            treeUri,
            DocumentsContract.getTreeDocumentId(treeUri),
        )
        for (segment in segments) {
            parent = findOrCreateDirectory(parent, segment)
                ?: throw IOException("Création du sous-dossier « $segment » impossible")
        }
        val documentUri = DocumentsContract.createDocument(resolver, parent, mimeType, name)
            ?: throw IOException("Création du fichier « $name » impossible")
        val stream = resolver.openOutputStream(documentUri)
            ?: throw IOException("Ouverture en écriture impossible pour « $name »")

        val location = buildLocation(segments, name)
        FdLog.i(LogTags.STORAGE, "Écriture dans le dossier choisi : $location")
        return Target(
            output = stream,
            location = location,
            onFinish = {},
            onAbort = { runCatching { DocumentsContract.deleteDocument(resolver, documentUri) } },
        )
    }

    private fun findOrCreateDirectory(parent: Uri, name: String): Uri? {
        val children = DocumentsContract.buildChildDocumentsUriUsingTree(
            parent,
            DocumentsContract.getDocumentId(parent),
        )
        val projection = arrayOf(
            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
            DocumentsContract.Document.COLUMN_MIME_TYPE,
        )
        resolver.query(children, projection, null, null, null)?.use { cursor ->
            while (cursor.moveToNext()) {
                val displayName = cursor.getString(1)
                val mimeType = cursor.getString(2)
                if (displayName == name && mimeType == DocumentsContract.Document.MIME_TYPE_DIR) {
                    return DocumentsContract.buildDocumentUriUsingTree(parent, cursor.getString(0))
                }
            }
        }
        return DocumentsContract.createDocument(
            resolver,
            parent,
            DocumentsContract.Document.MIME_TYPE_DIR,
            name,
        )
    }

    // --- 2. MediaStore (Android 10+) ----------------------------------------

    private fun openInMediaStore(segments: List<String>, name: String, mimeType: String): Target {
        val relativePath = buildString {
            append(Environment.DIRECTORY_DOWNLOADS).append('/').append(ROOT_FOLDER)
            segments.forEach { append('/').append(it) }
        }
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, name)
            put(MediaStore.Downloads.MIME_TYPE, mimeType)
            put(MediaStore.Downloads.RELATIVE_PATH, relativePath)
            // Tant que IS_PENDING vaut 1, le fichier n'est visible d'aucune autre
            // application : un transfert interrompu ne laisse pas de média à moitié
            // écrit dans la galerie.
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
        val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            ?: throw IOException("MediaStore a refusé la création de « $name »")
        val stream = resolver.openOutputStream(uri)
            ?: throw IOException("Ouverture en écriture impossible pour « $name »")

        val location = "$relativePath/$name"
        FdLog.i(LogTags.STORAGE, "Écriture via MediaStore : $location")
        return Target(
            output = stream,
            location = location,
            onFinish = {
                val done = ContentValues().apply { put(MediaStore.Downloads.IS_PENDING, 0) }
                runCatching { resolver.update(uri, done, null, null) }
                    .onFailure { FdLog.w(LogTags.STORAGE, "Publication MediaStore en échec", it) }
            },
            onAbort = { runCatching { resolver.delete(uri, null, null) } },
        )
    }

    // --- 3. Repli Android 8 / 9 ---------------------------------------------

    private fun openLegacyFile(segments: List<String>, name: String): Target {
        val canWritePublic = appContext.checkSelfPermission(
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
        ) == PackageManager.PERMISSION_GRANTED

        val root = if (canWritePublic) {
            File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), ROOT_FOLDER)
        } else {
            FdLog.w(
                LogTags.STORAGE,
                "Permission de stockage refusée : réception dans le dossier privé de l'application",
            )
            File(appContext.getExternalFilesDir(null) ?: appContext.filesDir, ROOT_FOLDER)
        }

        val directory = segments.fold(root) { current, segment -> File(current, segment) }
        if (!directory.exists() && !directory.mkdirs()) {
            throw IOException("Création du dossier ${directory.absolutePath} impossible")
        }

        var target = File(directory, name)
        var counter = 1
        while (target.exists()) {
            val base = name.substringBeforeLast('.', name)
            val extension = name.substringAfterLast('.', "")
            val candidate = if (extension.isEmpty()) "$base ($counter)" else "$base ($counter).$extension"
            target = File(directory, candidate)
            counter++
        }

        FdLog.i(LogTags.STORAGE, "Écriture directe : ${target.absolutePath}")
        return Target(
            output = FileOutputStream(target),
            location = target.absolutePath,
            onFinish = {},
            onAbort = { runCatching { target.delete() } },
        )
    }

    private fun buildLocation(segments: List<String>, name: String): String =
        (listOf(ROOT_FOLDER) + segments + name).joinToString("/")

    private companion object {
        const val ROOT_FOLDER = "FileDrop"
    }
}
