package com.filedrop.app.storage

import android.content.Context
import android.os.Build
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Réglages de l'application. Les seuls paramètres exposés en V1 sont ceux qui
 * changent réellement le comportement observable.
 */
class SettingsStore(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("filedrop_settings", Context.MODE_PRIVATE)

    private val _deviceName = MutableStateFlow(
        prefs.getString(KEY_DEVICE_NAME, null) ?: defaultDeviceName(),
    )
    val deviceName: StateFlow<String> = _deviceName

    private val _receivingEnabled = MutableStateFlow(prefs.getBoolean(KEY_RECEIVING, false))
    val receivingEnabled: StateFlow<Boolean> = _receivingEnabled

    /** Désactivé par défaut, comme exigé : rien n'arrive sans un geste explicite. */
    private val _autoAcceptKnownDevices = MutableStateFlow(prefs.getBoolean(KEY_AUTO_ACCEPT, false))
    val autoAcceptKnownDevices: StateFlow<Boolean> = _autoAcceptKnownDevices

    /** URI d'arborescence choisie via le sélecteur système, ou null pour le dossier par défaut. */
    private val _destinationTreeUri = MutableStateFlow(prefs.getString(KEY_DESTINATION, null))
    val destinationTreeUri: StateFlow<String?> = _destinationTreeUri

    fun setDeviceName(value: String) {
        val cleaned = value.trim().take(40).ifBlank { defaultDeviceName() }
        _deviceName.value = cleaned
        prefs.edit().putString(KEY_DEVICE_NAME, cleaned).apply()
    }

    fun setReceivingEnabled(value: Boolean) {
        _receivingEnabled.value = value
        prefs.edit().putBoolean(KEY_RECEIVING, value).apply()
    }

    fun setAutoAcceptKnownDevices(value: Boolean) {
        _autoAcceptKnownDevices.value = value
        prefs.edit().putBoolean(KEY_AUTO_ACCEPT, value).apply()
    }

    fun setDestinationTreeUri(value: String?) {
        _destinationTreeUri.value = value
        prefs.edit().putString(KEY_DESTINATION, value).apply()
    }

    private companion object {
        const val KEY_DEVICE_NAME = "device_name"
        const val KEY_RECEIVING = "receiving_enabled"
        const val KEY_AUTO_ACCEPT = "auto_accept_known"
        const val KEY_DESTINATION = "destination_tree_uri"

        fun defaultDeviceName(): String = Build.MODEL?.takeIf { it.isNotBlank() } ?: "Appareil Android"
    }
}
