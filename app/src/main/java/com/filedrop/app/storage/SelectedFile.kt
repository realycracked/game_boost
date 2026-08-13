package com.filedrop.app.storage

import android.net.Uri
import com.filedrop.app.transfer.protocol.FileMeta

/** Un fichier choisi par l'utilisateur, prêt à être envoyé. */
data class SelectedFile(
    val uri: Uri,
    val displayName: String,
    /** Chemin relatif dans le lot, vide pour un fichier isolé. */
    val relativePath: String,
    val size: Long,
    val mimeType: String,
) {
    fun toMeta(): FileMeta = FileMeta(
        name = displayName,
        relativePath = relativePath,
        size = size,
        mimeType = mimeType,
    )
}
