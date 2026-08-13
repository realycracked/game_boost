package com.filedrop.app.transport

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import com.filedrop.app.core.FdLog
import com.filedrop.app.core.LogTags
import com.filedrop.app.discovery.PeerDevice
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket

/**
 * Transport de référence de la V1 : TCP sur le réseau Wi-Fi local.
 *
 * C'est le seul transport réellement implémenté pour l'instant, et c'est un
 * choix, pas un raccourci : il est le plus rapide des trois, il ne demande
 * aucune permission d'exécution, et il se combine avec `NsdManager` pour la
 * découverte. Sa contrainte est réelle et doit être expliquée à l'utilisateur :
 * les deux appareils doivent être sur le même réseau Wi-Fi, et ce réseau ne
 * doit pas isoler ses clients les uns des autres (option « AP isolation »,
 * courante sur les Wi-Fi publics).
 */
class LanTcpTransport(private val context: Context) : TransferTransport {

    override val id = TransportId.WIFI_LAN
    override val displayName = "Wi-Fi local"

    override fun availability(): TransportAvailability {
        val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return TransportAvailability.Unavailable("Service réseau indisponible")
        val network = manager.activeNetwork
            ?: return TransportAvailability.Unavailable("Aucun réseau actif")
        val capabilities = manager.getNetworkCapabilities(network)
            ?: return TransportAvailability.Unavailable("État du réseau inconnu")

        return when {
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ->
                TransportAvailability.Available("Wi-Fi", ESTIMATED_WIFI_THROUGHPUT)

            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) ->
                TransportAvailability.Available("Ethernet", ESTIMATED_WIFI_THROUGHPUT)

            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ->
                TransportAvailability.Unavailable(
                    "Connexion en données mobiles : les appareils du réseau local ne sont pas joignables",
                )

            else -> TransportAvailability.Unavailable("Pas de réseau Wi-Fi")
        }
    }

    override fun listen(): TransportServer {
        // Port 0 : le système choisit un port libre, qui sera publié via mDNS.
        val serverSocket = ServerSocket()
        serverSocket.reuseAddress = true
        serverSocket.bind(InetSocketAddress(0))
        FdLog.i(LogTags.TRANSPORT, "Écoute TCP ouverte sur le port ${serverSocket.localPort}")
        return TcpServer(serverSocket)
    }

    override fun connect(peer: PeerDevice, timeoutMs: Int): TransportConnection {
        val host = peer.host
            ?: throw IOException("Adresse de ${peer.displayName} inconnue : la résolution mDNS n'a pas abouti")
        FdLog.i(LogTags.TRANSPORT, "Connexion TCP vers ${peer.displayName} ($host:${peer.port})")
        val socket = Socket()
        try {
            socket.tcpNoDelay = true
            socket.connect(InetSocketAddress(host, peer.port), timeoutMs)
            socket.soTimeout = READ_TIMEOUT_MS
        } catch (error: IOException) {
            runCatching { socket.close() }
            throw IOException("Connexion impossible vers $host:${peer.port} — ${error.message}", error)
        }
        return TcpConnection(socket)
    }

    private class TcpServer(private val serverSocket: ServerSocket) : TransportServer {
        override val localPort: Int get() = serverSocket.localPort

        override fun accept(): TransportConnection {
            val socket = serverSocket.accept()
            socket.tcpNoDelay = true
            socket.soTimeout = READ_TIMEOUT_MS
            return TcpConnection(socket)
        }

        override fun close() {
            runCatching { serverSocket.close() }
        }
    }

    private class TcpConnection(private val socket: Socket) : TransportConnection {
        override val input: InputStream = socket.getInputStream().buffered(STREAM_BUFFER)
        override val output: OutputStream = socket.getOutputStream().buffered(STREAM_BUFFER)
        override val remoteDescription: String =
            "${socket.inetAddress?.hostAddress ?: "?"}:${socket.port}"

        override fun close() {
            runCatching { output.flush() }
            runCatching { socket.close() }
        }
    }

    private companion object {
        /** Ordre de grandeur d'un Wi-Fi domestique : sert uniquement à classer les transports. */
        const val ESTIMATED_WIFI_THROUGHPUT = 12L * 1024 * 1024

        /**
         * Généreux : l'utilisateur d'en face peut mettre du temps à répondre à la
         * notification, et le socket ne doit pas expirer pendant ce temps.
         */
        const val READ_TIMEOUT_MS = 120_000

        const val STREAM_BUFFER = 128 * 1024
    }
}
