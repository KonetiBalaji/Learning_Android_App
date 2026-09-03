package com.konetibalaji.learning

import androidx.compose.foundation.layout.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp

fun selectionGridColumns(width: Float, fontScale: Float, cellWidth: Float, maximum: Int): Int {
    require(width.isFinite() && width >= 0 && fontScale.isFinite() && fontScale > 0)
    require(cellWidth.isFinite() && cellWidth > 0 && maximum in 1..12)
    return ((width + 12) / (cellWidth * fontScale.coerceAtLeast(1f) + 12)).toInt().coerceIn(1, maximum)
}

/** Small selection lists share the page scroll; no fixed-height nested viewport. */
@Composable
fun <T> AccessibleSelectionGrid(items: List<T>, cellWidth: Float, maximum: Int, content: @Composable (T) -> Unit) {
    val fontScale = LocalDensity.current.fontScale
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val columns = selectionGridColumns(maxWidth.value, fontScale, cellWidth, maximum)
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items.chunked(columns).forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    row.forEach { item -> Box(Modifier.weight(1f)) { content(item) } }
                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
    }
}
