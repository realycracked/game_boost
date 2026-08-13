package com.filedrop.app.transport

import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.core.formatBytes

data class TransportStatus(
    val id: TransportId,
    val displayName: String,
    val availability: TransportAvailability,
)

/**
 * Choisit le transport à utiliser, et surtout **explique** son choix.
 *
 * La règle est simple et volontairement lisible : parmi les transports
 * réellement disponibles à cet instant, celui dont le débit estimé est le plus
 * élevé gagne. C'est ce qui garantit qu'un envoi de plusieurs Go ne partira
 * jamais par Bluetooth si le Wi-Fi répond.
 *
 * Chaque évaluation est journalisée : sur un téléphone sans PC, la trace
 * « pourquoi ce transport et pas l'autre » est la seule façon de comprendre un
 * échec de connexion.
 */
class TransportManager(private val transports: List<TransferTransport>) {

    fun statuses(): List<TransportStatus> = transports.map { transport ->
        TransportStatus(transport.id, transport.displayName, transport.availability())
    }

    fun byId(id: TransportId): TransferTransport? = transports.firstOrNull { it.id == id }

    /**
     * Renvoie le meilleur transport disponible, ou `null` si aucun ne l'est.
     * [totalBytes] ne sert pour l'instant qu'à la journalisation, mais c'est le
     * point d'entrée prévu pour une règle plus fine (petit lot par Bluetooth,
     * gros lot par Wi-Fi) quand les autres transports existeront.
     */
    fun selectBest(totalBytes: Long = 0): TransferTransport? {
        val evaluated = transports.map { it to it.availability() }

        evaluated.forEach { (transport, availability) ->
            when (availability) {
                is TransportAvailability.Available -> FdLog.i(
                    LogTags.TRANSPORT,
                    "${transport.displayName} : disponible (${availability.details}, " +
                        "~${formatBytes(availability.estimatedBytesPerSecond)}/s)",
                )

                is TransportAvailability.Unavailable -> FdLog.i(
                    LogTags.TRANSPORT,
                    "${transport.displayName} : écarté — ${availability.reason}",
                )
            }
        }

        val best = evaluated
            .mapNotNull { (transport, availability) ->
                (availability as? TransportAvailability.Available)?.let { transport to it }
            }
            .maxByOrNull { it.second.estimatedBytesPerSecond }

        if (best == null) {
            FdLog.w(LogTags.TRANSPORT, "Aucun transport disponible : transfert impossible pour l'instant")
            return null
        }
        FdLog.i(
            LogTags.TRANSPORT,
            "Transport retenu : ${best.first.displayName}" +
                if (totalBytes > 0) " pour ${formatBytes(totalBytes)}" else "",
        )
        return best.first
    }
}
