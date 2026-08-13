package com.filedrop.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.filedrop.app.AppContainer
import com.filedrop.app.R
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogLevel
import com.filedrop.app.core.formatBytes
import com.filedrop.app.core.formatDuration
import com.filedrop.app.core.formatFileCount
import com.filedrop.app.core.formatSpeed
import com.filedrop.app.discovery.PeerDevice
import com.filedrop.app.history.TransferDirection
import com.filedrop.app.history.TransferOutcome
import com.filedrop.app.storage.SelectedFile
import com.filedrop.app.transfer.SessionStatus
import com.filedrop.app.transfer.TransferSession
import com.filedrop.app.transport.TransportAvailability
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FileDropApp(
    container: AppContainer,
    onPickFiles: () -> Unit,
    onPickDestination: () -> Unit,
    onStartReceiving: () -> Unit,
    onStopReceiving: () -> Unit,
    onSend: (PeerDevice, List<SelectedFile>) -> Unit,
    onCancel: (String) -> Unit,
) {
    val ui = container.ui
    val peers by container.discovery.peers.collectAsState()
    val sessions by container.engine.sessions.collectAsState()
    val receiving by container.engine.isReceiving.collectAsState()
    val discovering by container.discovery.isDiscovering.collectAsState()

    val pendingRequest = sessions.firstOrNull { it.isPendingDecision }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(titleFor(ui.route)) },
                navigationIcon = {
                    if (ui.route != Route.HOME) {
                        IconButton(onClick = { ui.route = Route.HOME }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Retour")
                        }
                    }
                },
                actions = {
                    if (ui.route == Route.HOME) {
                        IconButton(onClick = { container.discovery.refresh() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Rechercher")
                        }
                    }
                },
            )
        },
    ) { padding ->
        Box(Modifier.padding(padding)) {
            when (ui.route) {
                Route.HOME -> HomeScreen(
                    peers = peers,
                    sessions = sessions,
                    receiving = receiving,
                    discovering = discovering,
                    onRefresh = { container.discovery.refresh() },
                    onPickFiles = onPickFiles,
                    onToggleReceiving = { if (receiving) onStopReceiving() else onStartReceiving() },
                    onPeerClick = { peer ->
                        ui.selectedPeer = peer
                        if (ui.pendingFiles.isEmpty()) onPickFiles() else ui.route = Route.SEND
                    },
                    onNavigate = { ui.route = it },
                    onOpenSession = { ui.route = Route.TRANSFER },
                )

                Route.SEND -> SendScreen(
                    files = ui.pendingFiles,
                    peers = peers,
                    selectedPeer = ui.selectedPeer,
                    onSelectPeer = { ui.selectedPeer = it },
                    onRefresh = { container.discovery.refresh() },
                    onSend = {
                        val peer = ui.selectedPeer
                        if (peer != null && ui.pendingFiles.isNotEmpty()) {
                            onSend(peer, ui.pendingFiles)
                            ui.pendingFiles = emptyList()
                            ui.route = Route.TRANSFER
                        }
                    },
                    onCancel = { ui.reset() },
                )

                Route.TRANSFER -> TransferScreen(
                    sessions = sessions,
                    onCancel = onCancel,
                    onClose = { ui.route = Route.HOME },
                )

                Route.HISTORY -> HistoryScreen(container)
                Route.DEVICES -> KnownDevicesScreen(container)
                Route.SETTINGS -> SettingsScreen(container, onPickDestination)
                Route.LOGS -> LogScreen()
            }
        }
    }

    if (pendingRequest != null) {
        IncomingRequestDialog(
            session = pendingRequest,
            onAccept = { container.engine.respond(pendingRequest.id, true) },
            onRefuse = { container.engine.respond(pendingRequest.id, false) },
        )
    }

    ui.lastError?.let { message ->
        AlertDialog(
            onDismissRequest = { ui.lastError = null },
            confirmButton = { TextButton(onClick = { ui.lastError = null }) { Text("Fermer") } },
            title = { Text("FileDrop") },
            text = { Text(message) },
        )
    }
}

private fun titleFor(route: Route) = when (route) {
    Route.HOME -> "FileDrop"
    Route.SEND -> "Envoyer"
    Route.TRANSFER -> "Transfert"
    Route.HISTORY -> "Historique"
    Route.DEVICES -> "Appareils connus"
    Route.SETTINGS -> "Paramètres"
    Route.LOGS -> "Journal"
}

// --- Accueil ----------------------------------------------------------------

@Composable
private fun HomeScreen(
    peers: List<PeerDevice>,
    sessions: List<TransferSession>,
    receiving: Boolean,
    discovering: Boolean,
    onRefresh: () -> Unit,
    onPickFiles: () -> Unit,
    onToggleReceiving: () -> Unit,
    onPeerClick: (PeerDevice) -> Unit,
    onNavigate: (Route) -> Unit,
    onOpenSession: () -> Unit,
) {
    val active = sessions.filter { it.isActive }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(
                modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_filedrop_logo),
                    contentDescription = null,
                    tint = androidx.compose.ui.graphics.Color.Unspecified,
                    modifier = Modifier.size(96.dp),
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = when {
                        peers.isNotEmpty() -> "${peers.size} appareil(s) à proximité"
                        discovering -> "Recherche en cours…"
                        else -> "Aucun appareil détecté"
                    },
                    style = MaterialTheme.typography.titleMedium,
                )
                if (peers.isEmpty()) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = "Les deux appareils doivent être sur le même réseau Wi-Fi, " +
                            "et FileDrop doit être ouvert ou en réception sur l'autre appareil.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Spacer(Modifier.height(12.dp))
                OutlinedButton(onClick = onRefresh) { Text("Rechercher") }
            }
        }

        if (active.isNotEmpty()) {
            item {
                Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onOpenSession)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Transfert en cours", style = MaterialTheme.typography.titleSmall)
                        Spacer(Modifier.height(6.dp))
                        active.forEach { SessionSummary(it) }
                    }
                }
            }
        }

        items(peers, key = { it.serviceName }) { peer ->
            PeerRow(peer = peer, onClick = { onPeerClick(peer) })
        }

        item { Spacer(Modifier.height(8.dp)) }

        item {
            Card(Modifier.fillMaxWidth()) {
                Column {
                    ActionRow("Envoyer un fichier", "Choisir des fichiers à envoyer", onPickFiles)
                    HorizontalDivider()
                    ActionRow(
                        title = if (receiving) "Recevoir : activé" else "Recevoir",
                        subtitle = if (receiving) {
                            "Visible par les appareils du réseau"
                        } else {
                            "Rendre cet appareil visible et accepter les transferts"
                        },
                        onClick = onToggleReceiving,
                    )
                }
            }
        }

        item {
            Card(Modifier.fillMaxWidth()) {
                Column {
                    ActionRow("Historique", null) { onNavigate(Route.HISTORY) }
                    HorizontalDivider()
                    ActionRow("Appareils connus", null) { onNavigate(Route.DEVICES) }
                    HorizontalDivider()
                    ActionRow("Paramètres", null) { onNavigate(Route.SETTINGS) }
                    HorizontalDivider()
                    ActionRow("Journal", "Diagnostic des transferts") { onNavigate(Route.LOGS) }
                }
            }
        }
    }
}

@Composable
private fun ActionRow(title: String, subtitle: String?, onClick: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 14.dp),
    ) {
        Text(title, style = MaterialTheme.typography.bodyLarge)
        if (subtitle != null) {
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun PeerRow(peer: PeerDevice, onClick: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_filedrop_logo),
                    contentDescription = null,
                    tint = androidx.compose.ui.graphics.Color.Unspecified,
                    modifier = Modifier.size(30.dp),
                )
            }
            Spacer(Modifier.size(12.dp))
            Column(Modifier.weight(1f)) {
                Text(peer.displayName, style = MaterialTheme.typography.titleSmall)
                Text(
                    peer.model,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    "Empreinte ${peer.fingerprint}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                if (peer.isReachable) "Disponible" else "Résolution…",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}

// --- Envoi ------------------------------------------------------------------

@Composable
private fun SendScreen(
    files: List<SelectedFile>,
    peers: List<PeerDevice>,
    selectedPeer: PeerDevice?,
    onSelectPeer: (PeerDevice) -> Unit,
    onRefresh: () -> Unit,
    onSend: () -> Unit,
    onCancel: () -> Unit,
) {
    val totalBytes = files.sumOf { it.size }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("Envoyer vers", style = MaterialTheme.typography.labelLarge)
        Text(
            selectedPeer?.displayName ?: "Choisissez un appareil",
            style = MaterialTheme.typography.headlineSmall,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            "${formatFileCount(files.size)} — ${formatBytes(totalBytes)}",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Spacer(Modifier.height(12.dp))
        HorizontalDivider()
        Spacer(Modifier.height(12.dp))

        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            item {
                Text("Appareils à proximité", style = MaterialTheme.typography.titleSmall)
            }
            if (peers.isEmpty()) {
                item {
                    Column {
                        Text(
                            "Aucun appareil détecté.",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Spacer(Modifier.height(8.dp))
                        OutlinedButton(onClick = onRefresh) { Text("Rechercher") }
                    }
                }
            }
            items(peers, key = { it.serviceName }) { peer ->
                Card(
                    modifier = Modifier.fillMaxWidth().clickable { onSelectPeer(peer) },
                    colors = if (peer.serviceName == selectedPeer?.serviceName) {
                        CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    } else {
                        CardDefaults.cardColors()
                    },
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text(peer.displayName, style = MaterialTheme.typography.titleSmall)
                        Text(
                            peer.model,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }

            if (files.isNotEmpty()) {
                item {
                    Spacer(Modifier.height(8.dp))
                    Text("Fichiers", style = MaterialTheme.typography.titleSmall)
                }
                items(files.take(50)) { file ->
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            file.displayName,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text(formatBytes(file.size), style = MaterialTheme.typography.labelSmall)
                    }
                }
                if (files.size > 50) {
                    item {
                        Text(
                            "… et ${files.size - 50} autre(s)",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f)) { Text("Annuler") }
            Button(
                onClick = onSend,
                enabled = selectedPeer != null && files.isNotEmpty(),
                modifier = Modifier.weight(1f),
            ) { Text("Envoyer") }
        }
    }
}

// --- Transfert ---------------------------------------------------------------

@Composable
private fun TransferScreen(
    sessions: List<TransferSession>,
    onCancel: (String) -> Unit,
    onClose: () -> Unit,
) {
    if (sessions.isEmpty()) {
        Column(Modifier.fillMaxSize().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Aucun transfert.", style = MaterialTheme.typography.bodyLarge)
            Spacer(Modifier.height(12.dp))
            OutlinedButton(onClick = onClose) { Text("Retour") }
        }
        return
    }

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        items(sessions.sortedByDescending { it.startedAtMs }, key = { it.id }) { session ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    SessionSummary(session)
                    if (session.isActive) {
                        Spacer(Modifier.height(12.dp))
                        OutlinedButton(onClick = { onCancel(session.id) }) { Text("Annuler") }
                    }
                }
            }
        }
    }
}

@Composable
private fun SessionSummary(session: TransferSession) {
    Column(Modifier.fillMaxWidth()) {
        Text(
            (if (session.outgoing) "Envoi vers " else "Réception depuis ") + session.peerName,
            style = MaterialTheme.typography.titleSmall,
        )
        Text(
            "${formatFileCount(session.fileCount)} — ${formatBytes(session.totalBytes)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(8.dp))

        when (session.status) {
            SessionStatus.CONNECTING -> {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.size(8.dp))
                    Text("Connexion…", style = MaterialTheme.typography.bodySmall)
                }
            }

            SessionStatus.AWAITING_DECISION -> Text(
                if (session.outgoing) "En attente de l'acceptation" else "En attente de votre réponse",
                style = MaterialTheme.typography.bodySmall,
            )

            SessionStatus.TRANSFERRING -> {
                LinearProgressIndicator(
                    progress = { session.progress },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    "${formatBytes(session.transferredBytes)} / ${formatBytes(session.totalBytes)}  " +
                        "•  ${(session.progress * 100).toInt()} %",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    formatSpeed(session.bytesPerSecond) +
                        if (session.etaSeconds >= 0) {
                            "  •  environ ${formatDuration(session.etaSeconds)} restantes"
                        } else {
                            ""
                        },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (session.currentFileName.isNotBlank()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Fichier ${session.currentFileIndex + 1}/${session.fileCount} : " +
                            session.currentFileName,
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    LinearProgressIndicator(
                        progress = { session.currentFileProgress },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }

            SessionStatus.COMPLETED -> Text("Terminé", style = MaterialTheme.typography.bodySmall)
            SessionStatus.REFUSED -> Text("Refusé", style = MaterialTheme.typography.bodySmall)
            SessionStatus.CANCELLED -> Text("Annulé", style = MaterialTheme.typography.bodySmall)
            SessionStatus.FAILED -> Text(
                "Échec : ${session.message}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
}

@Composable
private fun IncomingRequestDialog(
    session: TransferSession,
    onAccept: () -> Unit,
    onRefuse: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onRefuse,
        title = { Text("${session.peerName} souhaite vous envoyer") },
        text = {
            Column {
                Text("${formatFileCount(session.fileCount)} — ${formatBytes(session.totalBytes)}")
                Spacer(Modifier.height(6.dp))
                Text(
                    session.peerModel,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    "Empreinte ${session.peerFingerprint}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (session.previewNames.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    session.previewNames.take(6).forEach {
                        Text(it, style = MaterialTheme.typography.labelSmall, maxLines = 1)
                    }
                }
            }
        },
        confirmButton = { Button(onClick = onAccept) { Text("Accepter") } },
        dismissButton = { TextButton(onClick = onRefuse) { Text("Refuser") } },
    )
}

// --- Historique --------------------------------------------------------------

@Composable
private fun HistoryScreen(container: AppContainer) {
    val records by container.history.records.collectAsState()
    val format = remember { SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()) }

    if (records.isEmpty()) {
        EmptyMessage("Aucun transfert pour l'instant.")
        return
    }

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(records, key = { it.id }) { record ->
            Card(Modifier.fillMaxWidth()) {
                Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        if (record.direction == TransferDirection.SENT) "↑" else "↓",
                        style = MaterialTheme.typography.titleLarge,
                    )
                    Spacer(Modifier.size(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            "${formatBytes(record.totalBytes)} — ${record.peerName}",
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Text(
                            "${formatFileCount(record.fileCount)} • ${format.format(Date(record.timestampMs))}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (record.outcome != TransferOutcome.COMPLETED) {
                            Text(
                                when (record.outcome) {
                                    TransferOutcome.REFUSED -> "Refusé"
                                    TransferOutcome.CANCELLED -> "Annulé"
                                    TransferOutcome.FAILED -> "Échec : ${record.detail}"
                                    else -> ""
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.error,
                            )
                        }
                    }
                }
            }
        }
        item {
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = { container.history.clearHistory() }) {
                Text("Effacer l'historique")
            }
        }
    }
}

@Composable
private fun KnownDevicesScreen(container: AppContainer) {
    val devices by container.history.knownDevices.collectAsState()
    val format = remember { SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault()) }

    if (devices.isEmpty()) {
        EmptyMessage("Aucun appareil connu. Un appareil est mémorisé après un transfert réussi.")
        return
    }

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(devices, key = { it.fingerprint }) { device ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp)) {
                    Text(device.name, style = MaterialTheme.typography.titleSmall)
                    Text(
                        "Dernier transfert : ${format.format(Date(device.lastTransferMs))}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        "Empreinte ${device.fingerprint} • ${device.transferCount} transfert(s)",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
        item {
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = { container.history.forgetDevices() }) {
                Text("Oublier tous les appareils")
            }
        }
    }
}

// --- Paramètres --------------------------------------------------------------

@Composable
private fun SettingsScreen(container: AppContainer, onPickDestination: () -> Unit) {
    val deviceName by container.settings.deviceName.collectAsState()
    val autoAccept by container.settings.autoAcceptKnownDevices.collectAsState()
    val destination by container.settings.destinationTreeUri.collectAsState()
    var nameField by remember { mutableStateOf(deviceName) }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text("Nom de cet appareil", style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = nameField,
            onValueChange = { nameField = it },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(8.dp))
        Button(onClick = { container.settings.setDeviceName(nameField) }) { Text("Enregistrer") }

        Spacer(Modifier.height(20.dp))
        HorizontalDivider()
        Spacer(Modifier.height(20.dp))

        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Accepter automatiquement", style = MaterialTheme.typography.titleSmall)
                Text(
                    "Uniquement pour les appareils avec lesquels un transfert a déjà abouti. " +
                        "Désactivé par défaut.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(
                checked = autoAccept,
                onCheckedChange = { container.settings.setAutoAcceptKnownDevices(it) },
            )
        }

        Spacer(Modifier.height(20.dp))
        HorizontalDivider()
        Spacer(Modifier.height(20.dp))

        Text("Dossier de réception", style = MaterialTheme.typography.titleSmall)
        Text(
            destination ?: "Par défaut : Download/FileDrop",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onPickDestination) { Text("Choisir un dossier") }
            if (destination != null) {
                TextButton(onClick = { container.settings.setDestinationTreeUri(null) }) {
                    Text("Réinitialiser")
                }
            }
        }

        Spacer(Modifier.height(20.dp))
        HorizontalDivider()
        Spacer(Modifier.height(20.dp))

        Text("Transports", style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(6.dp))
        container.transportManager.statuses().forEach { status ->
            val (label, color) = when (val availability = status.availability) {
                is TransportAvailability.Available ->
                    "disponible (${availability.details})" to MaterialTheme.colorScheme.primary

                is TransportAvailability.Unavailable ->
                    availability.reason to MaterialTheme.colorScheme.onSurfaceVariant
            }
            Text("${status.displayName} : $label", style = MaterialTheme.typography.bodySmall, color = color)
        }

        Spacer(Modifier.height(20.dp))
        Text(
            "Empreinte de cet appareil : ${container.identityStore.identity.fingerprint}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            "Port d'écoute : ${container.engine.listeningPort().takeIf { it > 0 } ?: "inactif"}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

// --- Journal -----------------------------------------------------------------

@Composable
private fun LogScreen() {
    val entries by FdLog.entries.collectAsState()
    val format = remember { SimpleDateFormat("HH:mm:ss", Locale.getDefault()) }

    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("${entries.size} entrée(s)", style = MaterialTheme.typography.labelMedium)
            Spacer(Modifier.weight(1f))
            TextButton(onClick = { FdLog.clear() }) { Text("Effacer") }
        }
        HorizontalDivider()
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp),
            reverseLayout = true,
        ) {
            items(entries.reversed()) { entry ->
                Text(
                    "${format.format(Date(entry.timeMs))} ${entry.tag}: ${entry.message}",
                    style = MaterialTheme.typography.labelSmall,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = if (entry.level == LogLevel.ERROR) FontWeight.Bold else FontWeight.Normal,
                    color = when (entry.level) {
                        LogLevel.ERROR -> MaterialTheme.colorScheme.error
                        LogLevel.WARN -> MaterialTheme.colorScheme.secondary
                        else -> MaterialTheme.colorScheme.onSurface
                    },
                    modifier = Modifier.padding(vertical = 2.dp),
                )
            }
        }
    }
}

@Composable
private fun EmptyMessage(message: String) {
    Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
        Text(
            message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
