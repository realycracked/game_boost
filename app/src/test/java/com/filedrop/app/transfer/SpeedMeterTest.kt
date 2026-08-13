package com.filedrop.app.transfer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SpeedMeterTest {

    @Test
    fun `la premiere mesure ne produit pas de debit`() {
        val meter = SpeedMeter()
        assertEquals(0L, meter.update(0, 1_000))
    }

    @Test
    fun `le debit se rapproche de la valeur reelle`() {
        val meter = SpeedMeter()
        meter.update(0, 1_000)
        var speed = 0L
        var bytes = 0L
        // 10 Mo/s pendant 10 secondes, mesuré chaque seconde.
        for (second in 2..11) {
            bytes += 10_000_000
            speed = meter.update(bytes, second * 1000L)
        }
        assertTrue("débit mesuré : $speed", speed in 8_000_000..12_000_000)
    }

    @Test
    fun `le temps restant est coherent`() {
        val meter = SpeedMeter()
        meter.update(0, 1_000)
        meter.update(10_000_000, 2_000)
        val eta = meter.etaSeconds(100_000_000)
        assertTrue("eta : $eta", eta in 5..20)
    }

    @Test
    fun `sans debit connu le temps restant est inconnu`() {
        assertEquals(-1L, SpeedMeter().etaSeconds(1_000))
    }
}
