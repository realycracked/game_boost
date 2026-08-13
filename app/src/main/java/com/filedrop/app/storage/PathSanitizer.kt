package com.filedrop.app.storage

/**
 * Assainit les noms et chemins reçus du réseau.
 *
 * Ce n'est pas de la cosmétique : sans cela, un appareil malveillant pourrait
 * annoncer un chemin relatif du type `../../databases/` et faire écrire le
 * fichier hors du dossier de réception. Tout ce qui vient d'en face passe par
 * ici avant de toucher le système de fichiers.
 */
object PathSanitizer {

    private const val MAX_SEGMENT_LENGTH = 120
    private const val MAX_DEPTH = 16

    // Séparateurs de chemin, caractères interdits par FAT/exFAT, et caractères
    // de contrôle. Les espaces et les tirets sont légitimes et sont conservés.
    private val FORBIDDEN = Regex("""[\\/:*?"<>|\x00-\x1F]""")

    fun sanitizeName(raw: String): String {
        val cleaned = FORBIDDEN.replace(raw, "_").trim().trimEnd('.')
        val limited = if (cleaned.length > MAX_SEGMENT_LENGTH) {
            val extension = cleaned.substringAfterLast('.', "")
            val base = cleaned.substringBeforeLast('.', cleaned)
            val keep = (MAX_SEGMENT_LENGTH - extension.length - 1).coerceAtLeast(1)
            if (extension.isEmpty()) base.take(MAX_SEGMENT_LENGTH) else "${base.take(keep)}.$extension"
        } else {
            cleaned
        }
        return when {
            limited.isEmpty() || limited == "." || limited == ".." -> "fichier"
            else -> limited
        }
    }

    /** Découpe un chemin relatif en segments sûrs. Renvoie une liste vide si le chemin est vide. */
    fun sanitizeRelativePath(raw: String): List<String> =
        raw.split('/', '\\')
            .map { it.trim() }
            .filter { it.isNotEmpty() && it != "." && it != ".." }
            .map { sanitizeName(it) }
            .take(MAX_DEPTH)

    fun joinRelativePath(raw: String): String = sanitizeRelativePath(raw).joinToString("/")
}
