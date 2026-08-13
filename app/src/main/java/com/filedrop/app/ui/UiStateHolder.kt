package com.filedrop.app.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.filedrop.app.discovery.PeerDevice
import com.filedrop.app.storage.SelectedFile

enum class Route { HOME, SEND, TRANSFER, HISTORY, DEVICES, SETTINGS, LOGS }

/**
 * État de navigation et sélection en cours.
 *
 * Volontairement porté par le conteneur applicatif plutôt que par l'activité :
 * une rotation d'écran ne doit pas faire perdre une sélection de 1 400 fichiers
 * arrivée par le menu Partager.
 */
class UiStateHolder {
    var route by mutableStateOf(Route.HOME)
    var pendingFiles by mutableStateOf<List<SelectedFile>>(emptyList())
    var selectedPeer by mutableStateOf<PeerDevice?>(null)
    var lastError by mutableStateOf<String?>(null)

    fun reset() {
        pendingFiles = emptyList()
        selectedPeer = null
        route = Route.HOME
    }
}
