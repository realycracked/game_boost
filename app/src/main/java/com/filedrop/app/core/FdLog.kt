package com.filedrop.app.core

import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

enum class LogLevel(val symbol: Char) { DEBUG('D'), INFO('I'), WARN('W'), ERROR('E') }

data class LogEntry(
    val timeMs: Long,
    val level: LogLevel,
    val tag: String,
    val message: String,
)

/**
 * Journalisation de FileDrop.
 *
 * Tout passe par ici plutôt que par [Log] directement, pour deux raisons :
 *
 *  1. les messages partent dans logcat (`adb logcat -s FD:*`) ;
 *  2. ils sont aussi conservés dans un tampon circulaire consultable
 *     *depuis le téléphone*, via l'écran « Journal » de l'application.
 *
 * Ce second point n'est pas un confort : quand on développe sans PC, `adb` n'est
 * pas disponible, et un journal interne est le seul moyen réaliste de
 * diagnostiquer un problème de découverte ou de transfert sur l'appareil.
 */
object FdLog {

    /** Nombre d'entrées conservées en mémoire. Au-delà, les plus anciennes sautent. */
    private const val MAX_ENTRIES = 1500

    private val lock = Any()
    private val buffer = ArrayDeque<LogEntry>()
    private val _entries = MutableStateFlow<List<LogEntry>>(emptyList())

    val entries: StateFlow<List<LogEntry>> = _entries

    fun d(tag: String, message: String) = log(LogLevel.DEBUG, tag, message, null)
    fun i(tag: String, message: String) = log(LogLevel.INFO, tag, message, null)
    fun w(tag: String, message: String, error: Throwable? = null) = log(LogLevel.WARN, tag, message, error)
    fun e(tag: String, message: String, error: Throwable? = null) = log(LogLevel.ERROR, tag, message, error)

    private fun log(level: LogLevel, tag: String, message: String, error: Throwable?) {
        val logcatTag = "FD/$tag"
        when (level) {
            LogLevel.DEBUG -> Log.d(logcatTag, message, error)
            LogLevel.INFO -> Log.i(logcatTag, message, error)
            LogLevel.WARN -> Log.w(logcatTag, message, error)
            LogLevel.ERROR -> Log.e(logcatTag, message, error)
        }
        val text = if (error == null) {
            message
        } else {
            "$message — ${error.javaClass.simpleName}: ${error.message}"
        }
        synchronized(lock) {
            buffer.addLast(LogEntry(System.currentTimeMillis(), level, tag, text))
            while (buffer.size > MAX_ENTRIES) {
                buffer.removeFirst()
            }
            _entries.value = buffer.toList()
        }
    }

    fun clear() {
        synchronized(lock) {
            buffer.clear()
            _entries.value = emptyList()
        }
    }

    /** Journal complet en texte, pour le bouton « Partager le journal ». */
    fun dump(): String {
        val format = SimpleDateFormat("HH:mm:ss.SSS", Locale.US)
        return _entries.value.joinToString("\n") { entry ->
            "${format.format(Date(entry.timeMs))} ${entry.level.symbol} ${entry.tag}: ${entry.message}"
        }
    }
}

/** Étiquettes de journal, une par sous-système : le filtrage reste lisible. */
object LogTags {
    const val APP = "App"
    const val DISCOVERY = "Discovery"
    const val TRANSPORT = "Transport"
    const val SECURITY = "Security"
    const val SEND = "Send"
    const val RECEIVE = "Receive"
    const val STORAGE = "Storage"
    const val SHARING = "Sharing"
    const val NOTIF = "Notif"
    const val SERVICE = "Service"
    const val UI = "Ui"
}
