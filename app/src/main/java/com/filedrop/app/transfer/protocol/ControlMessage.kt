package com.filedrop.app.transfer.protocol

/** Métadonnées d'un fichier telles qu'elles circulent sur le réseau. */
data class FileMeta(
    val name: String,
    /** Chemin relatif au sein du lot, vide pour un fichier isolé. Ex. `Jour 01`. */
    val relativePath: String,
    val size: Long,
    val mimeType: String,
)

/**
 * Messages du protocole FileDrop v1.
 *
 * Chaque trame du canal chiffré commence par un octet de type. Les données de
 * fichier passent par le même canal (type [ControlCodec.TYPE_FILE_DATA]) afin
 * de rester chiffrées elles aussi, mais elles ne sont jamais désérialisées :
 * le tampon est écrit tel quel sur le disque.
 */
sealed interface ControlMessage {

    /**
     * Proposition de transfert.
     *
     * L'offre ne contient qu'un résumé et un aperçu de quelques noms : la liste
     * complète pourrait dépasser la taille d'une trame sur un dossier de
     * plusieurs milliers de fichiers. Les métadonnées définitives de chaque
     * fichier arrivent dans [FileStart].
     */
    data class Offer(
        val sessionId: String,
        val deviceName: String,
        val deviceModel: String,
        val fileCount: Int,
        val totalBytes: Long,
        val previewNames: List<String>,
    ) : ControlMessage

    data object Accept : ControlMessage

    data class Reject(val reason: String) : ControlMessage

    data class FileStart(val index: Int, val meta: FileMeta) : ControlMessage

    data class FileEnd(val index: Int, val bytesSent: Long) : ControlMessage

    data object TransferEnd : ControlMessage

    data class Cancel(val reason: String) : ControlMessage

    /** Trame de données : [length] octets utiles, disponibles à partir de l'offset 1. */
    data class FileData(val length: Int) : ControlMessage
}
