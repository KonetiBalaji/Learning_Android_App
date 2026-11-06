package com.studycompanion

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.unit.dp

/** Decorative companion to the visible Saras tutor label. */
@Composable
internal fun TutorAvatar(speaking: Boolean) {
    val background = MaterialTheme.colorScheme.primaryContainer
    val face = MaterialTheme.colorScheme.onPrimaryContainer
    val mouthHeight by animateFloatAsState(if (speaking) 0.20f else 0.07f, label = "Tutor speaking")
    Canvas(Modifier.size(36.dp)) {
        val side = size.minDimension
        drawCircle(background)
        drawCircle(face, radius = side * 0.045f, center = Offset(side * 0.34f, side * 0.41f))
        drawCircle(face, radius = side * 0.045f, center = Offset(side * 0.66f, side * 0.41f))
        drawRoundRect(
            color = face,
            topLeft = Offset(side * 0.39f, side * (0.66f - mouthHeight / 2)),
            size = Size(side * 0.22f, side * mouthHeight),
            cornerRadius = CornerRadius(side * 0.06f),
        )
    }
}
