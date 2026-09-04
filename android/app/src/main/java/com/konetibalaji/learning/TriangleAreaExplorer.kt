package com.konetibalaji.learning

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class TriangleAreaModel(val base: Int, val height: Int) {
    init { require(base > 0 && height > 0 && base * height % 2 == 0) }
    val area: Int get() = base * height / 2
}

val triangleAreaModels = listOf(
    TriangleAreaModel(6, 4),
    TriangleAreaModel(8, 5),
    TriangleAreaModel(10, 6),
)

@Composable
fun TriangleAreaExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val model = triangleAreaModels[selected]
    val fill = MaterialTheme.colorScheme.primaryContainer
    val line = MaterialTheme.colorScheme.primary
    val guide = MaterialTheme.colorScheme.outline
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Explore triangle area", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select a base and perpendicular height. A triangle occupies half of the matching rectangle.")
            triangleAreaModels.forEachIndexed { index, item ->
                OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                    val label = "Base ${item.base}, height ${item.height}"
                    Text(if (selected == index) "Selected: $label" else label)
                }
            }
            Canvas(Modifier.fillMaxWidth().size(260.dp).semantics {
                contentDescription = "Triangle with base ${model.base}, perpendicular height ${model.height}, and area ${model.area} square units"
            }) {
                val left = size.width * .12f
                val right = size.width * .88f
                val bottom = size.height * .82f
                val top = size.height * .15f
                val apexX = size.width * .58f
                val path = Path().apply {
                    moveTo(left, bottom); lineTo(right, bottom); lineTo(apexX, top); close()
                }
                drawPath(path, fill)
                drawPath(path, line, style = Stroke(width = 7f))
                drawLine(guide, Offset(apexX, top), Offset(apexX, bottom), strokeWidth = 5f)
                val marker = size.minDimension * .045f
                drawLine(guide, Offset(apexX, bottom - marker), Offset(apexX + marker, bottom - marker), strokeWidth = 4f)
                drawLine(guide, Offset(apexX + marker, bottom - marker), Offset(apexX + marker, bottom), strokeWidth = 4f)
            }
            Text("Area = base × height ÷ 2", fontWeight = FontWeight.Bold)
            Text("${model.base} × ${model.height} ÷ 2 = ${model.area} square units",
                style = MaterialTheme.typography.titleMedium)
            Text("The height guide is perpendicular to the base; a sloping side is not the height.",
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Exploring the diagram does not submit an answer or change mastery.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
}
