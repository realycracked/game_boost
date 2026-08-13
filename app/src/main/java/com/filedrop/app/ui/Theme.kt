package com.filedrop.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Turquoise = Color(0xFF00C6A7)
private val Blue = Color(0xFF1E6FFF)

private val LightScheme = lightColorScheme(
    primary = Blue,
    onPrimary = Color.White,
    secondary = Turquoise,
    onSecondary = Color(0xFF04241F),
    background = Color(0xFFF7F9FC),
    onBackground = Color(0xFF10151F),
    surface = Color.White,
    onSurface = Color(0xFF10151F),
    surfaceVariant = Color(0xFFE9EEF7),
    onSurfaceVariant = Color(0xFF465065),
    error = Color(0xFFB3261E),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFF7FA9FF),
    onPrimary = Color(0xFF00214D),
    secondary = Turquoise,
    onSecondary = Color(0xFF04241F),
    background = Color(0xFF0B1220),
    onBackground = Color(0xFFE6EAF2),
    surface = Color(0xFF141C2B),
    onSurface = Color(0xFFE6EAF2),
    surfaceVariant = Color(0xFF232D40),
    onSurfaceVariant = Color(0xFFB4BECF),
    error = Color(0xFFF2B8B5),
)

@Composable
fun FileDropTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkScheme else LightScheme,
        content = content,
    )
}
