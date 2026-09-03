package com.konetibalaji.learning

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import org.junit.Assert.assertTrue
import org.junit.Test

class LearningThemeTest {
    private fun assertReadable(foreground: Color, background: Color) {
        val first = foreground.luminance().toDouble()
        val second = background.luminance().toDouble()
        val ratio = (maxOf(first, second) + 0.05) / (minOf(first, second) + 0.05)
        assertTrue("Text contrast is $ratio; expected at least 4.5", ratio >= 4.5)
    }

    @Test fun lightThemeTextPairsAreReadable() = verify(false)
    @Test fun darkThemeTextPairsAreReadable() = verify(true)

    private fun verify(dark: Boolean) {
        val scheme = learningColorScheme(dark)
        assertReadable(scheme.onSurface, scheme.surface)
        assertReadable(scheme.onSurfaceVariant, scheme.surfaceVariant)
        assertReadable(scheme.onPrimary, scheme.primary)
        assertReadable(scheme.onSecondaryContainer, scheme.secondaryContainer)
        assertReadable(scheme.onTertiaryContainer, scheme.tertiaryContainer)
        assertReadable(scheme.primary, scheme.surface)
        assertReadable(scheme.tertiary, scheme.surface)
        assertReadable(scheme.onSurface, scheme.surfaceVariant)
        assertReadable(scheme.primary, scheme.surfaceVariant)
        assertReadable(scheme.tertiary, scheme.surfaceVariant)
        assertReadable(scheme.error, scheme.surfaceVariant)
    }
}
