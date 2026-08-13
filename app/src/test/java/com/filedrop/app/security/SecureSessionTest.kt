package com.filedrop.app.security

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.Closeable
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference
import kotlin.random.Random

/**
 * Vérifie de bout en bout la poignée de main et le canal chiffré.
 *
 * Le test ouvre une vraie paire de sockets sur l'interface de bouclage : c'est
 * exactement le chemin emprunté en production par `LanTcpTransport`, et cela
 * fonctionne sur GitHub Actions sans émulateur ni appareil.
 */
class SecureSessionTest {

    private class Session(
        val client: Handshake.Result,
        val server: Handshake.Result,
        val clientIdentity: DeviceIdentity,
        val serverIdentity: DeviceIdentity,
        private val closeables: List<Closeable>,
    ) : Closeable {
        override fun close() = closeables.forEach { runCatching { it.close() } }
    }

    private fun establish(): Session {
        val clientIdentity = DeviceIdentity.generate()
        val serverIdentity = DeviceIdentity.generate()

        val listener = ServerSocket(0, 1, InetAddress.getLoopbackAddress())
        val serverResult = AtomicReference<Handshake.Result>()
        val serverError = AtomicReference<Throwable>()
        val serverSocket = AtomicReference<Socket>()

        val serverThread = Thread {
            try {
                val socket = listener.accept()
                serverSocket.set(socket)
                serverResult.set(
                    Handshake.asServer(
                        socket.getInputStream().buffered(BUFFER),
                        socket.getOutputStream().buffered(BUFFER),
                        serverIdentity,
                    ),
                )
            } catch (error: Throwable) {
                serverError.set(error)
            }
        }
        serverThread.start()

        val clientSocket = Socket(InetAddress.getLoopbackAddress(), listener.localPort)
        val client = Handshake.asClient(
            clientSocket.getInputStream().buffered(BUFFER),
            clientSocket.getOutputStream().buffered(BUFFER),
            clientIdentity,
        )
        serverThread.join(20_000)
        serverError.get()?.let { throw it }

        return Session(
            client = client,
            server = requireNotNull(serverResult.get()) { "La poignée de main serveur n'a pas abouti" },
            clientIdentity = clientIdentity,
            serverIdentity = serverIdentity,
            closeables = listOfNotNull(clientSocket, serverSocket.get(), listener),
        )
    }

    @Test
    fun `les deux camps s authentifient et voient la meme empreinte`() {
        establish().use { session ->
            assertEquals(session.serverIdentity.fingerprint, session.client.peerFingerprint)
            assertEquals(session.clientIdentity.fingerprint, session.server.peerFingerprint)
            assertNotEquals(session.client.peerFingerprint, session.server.peerFingerprint)
            assertTrue(
                session.client.peerFingerprint,
                session.client.peerFingerprint.matches(Regex("[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}")),
            )
        }
    }

    @Test
    fun `un message circule chiffre dans les deux sens`() {
        establish().use { session ->
            val fromClient = "Offre de transfert".toByteArray()
            session.client.channel.writeFrame(fromClient)
            assertArrayEquals(fromClient, session.server.channel.readFrame())

            val fromServer = "Accepté".toByteArray()
            session.server.channel.writeFrame(fromServer)
            assertArrayEquals(fromServer, session.client.channel.readFrame())
        }
    }

    /**
     * 8 Mio traversent le canal par blocs de 64 Kio. Le test vérifie l'intégrité
     * par empreinte SHA-256 : c'est la garantie que la découpe en trames, les
     * compteurs de nonce et le réassemblage sont corrects sur un flux long.
     */
    @Test
    fun `un gros flux passe par blocs sans etre charge en memoire`() {
        establish().use { session ->
            val chunk = Random(42).nextBytes(SecureChannel.CHUNK_SIZE)
            val chunkCount = 128
            val expected = MessageDigest.getInstance("SHA-256")
            repeat(chunkCount) { expected.update(chunk) }

            val actual = MessageDigest.getInstance("SHA-256")
            val receivedBytes = AtomicLong(0)
            val readerError = AtomicReference<Throwable>()

            val reader = Thread {
                try {
                    val buffer = ByteArray(SecureChannel.MAX_PLAINTEXT)
                    var total = 0L
                    repeat(chunkCount) {
                        val length = session.server.channel.readFrameInto(buffer)
                        check(length > 0) { "Trame vide reçue" }
                        actual.update(buffer, 0, length)
                        total += length
                    }
                    receivedBytes.set(total)
                } catch (error: Throwable) {
                    readerError.set(error)
                }
            }
            reader.start()

            repeat(chunkCount) { session.client.channel.writeFrame(chunk) }
            reader.join(120_000)
            readerError.get()?.let { throw it }

            assertEquals(chunk.size.toLong() * chunkCount, receivedBytes.get())
            assertArrayEquals(expected.digest(), actual.digest())
        }
    }

    /**
     * Une trame qui n'a pas été produite avec la bonne clé doit être rejetée par
     * le tag GCM : c'est ce qui rend une altération en vol détectable.
     */
    @Test
    fun `une trame non authentifiee est rejetee`() {
        val listener = ServerSocket(0, 1, InetAddress.getLoopbackAddress())
        val accepted = AtomicReference<Socket>()
        val thread = Thread { accepted.set(listener.accept()) }
        thread.start()
        val clientSocket = Socket(InetAddress.getLoopbackAddress(), listener.localPort)
        thread.join(10_000)
        val serverSocket = requireNotNull(accepted.get())

        val prefix = ByteArray(SecureChannel.NONCE_PREFIX_BYTES) { 9 }
        val sender = SecureChannel(
            input = clientSocket.getInputStream(),
            output = clientSocket.getOutputStream(),
            sendKey = ByteArray(SecureChannel.KEY_BYTES) { 1 },
            sendNoncePrefix = prefix,
            receiveKey = ByteArray(SecureChannel.KEY_BYTES) { 1 },
            receiveNoncePrefix = prefix,
        )
        val receiver = SecureChannel(
            input = serverSocket.getInputStream(),
            output = serverSocket.getOutputStream(),
            sendKey = ByteArray(SecureChannel.KEY_BYTES) { 2 },
            sendNoncePrefix = prefix,
            receiveKey = ByteArray(SecureChannel.KEY_BYTES) { 2 },
            receiveNoncePrefix = prefix,
        )

        sender.writeFrame("secret".toByteArray())
        try {
            receiver.readFrame()
            fail("Une trame non authentifiée aurait dû être rejetée")
        } catch (expected: java.security.GeneralSecurityException) {
            assertTrue(true)
        } finally {
            listOf(clientSocket, serverSocket, listener).forEach { runCatching { it.close() } }
        }
    }

    private companion object {
        const val BUFFER = 128 * 1024
    }
}
