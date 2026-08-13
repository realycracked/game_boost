package com.filedrop.app.core

import java.util.Locale

/**
 * Tailles affichées en unités décimales (ko = 1000 o), comme le fait Android
 * lui-même dans les paramètres de stockage : c'est ce que l'utilisateur voit
 * ailleurs sur son téléphone.
 */
fun formatBytes(bytes: Long): String {
    if (bytes < 0) return "—"
    if (bytes < 1000) return "$bytes o"
    val units = arrayOf("ko", "Mo", "Go", "To")
    var value = bytes.toDouble()
    var index = -1
    while (value >= 1000 && index < units.size - 1) {
        value /= 1000.0
        index++
    }
    val locale = Locale.getDefault()
    return if (value >= 100) {
        String.format(locale, "%.0f %s", value, units[index])
    } else {
        String.format(locale, "%.1f %s", value, units[index])
    }
}

fun formatSpeed(bytesPerSecond: Long): String =
    if (bytesPerSecond <= 0) "—" else "${formatBytes(bytesPerSecond)}/s"

fun formatDuration(seconds: Long): String = when {
    seconds < 0 -> "—"
    seconds < 60 -> "$seconds s"
    seconds < 3600 -> "${seconds / 60} min"
    else -> {
        val hours = seconds / 3600
        val minutes = (seconds % 3600) / 60
        if (minutes == 0L) "$hours h" else "$hours h $minutes min"
    }
}

fun formatFileCount(count: Int): String = if (count <= 1) "$count fichier" else "$count fichiers"
