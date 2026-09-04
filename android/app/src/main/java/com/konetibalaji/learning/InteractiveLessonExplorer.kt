package com.konetibalaji.learning

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

enum class ExplorerKind { FRACTIONS, CELL_ORGANELLES }

fun explorerKind(subjectId: String?, chapterId: String?): ExplorerKind? = when {
    subjectId == "math" && chapterId == "fractions" -> ExplorerKind.FRACTIONS
    subjectId == "science" && chapterId == "cells" -> ExplorerKind.CELL_ORGANELLES
    else -> null
}

data class OrganelleLesson(val name: String, val function: String, val evidence: String)

val organelleLessons = listOf(
    OrganelleLesson("Nucleus", "Stores most of the cell's DNA and helps direct cell activities.",
        "Chromosomes are kept inside the nucleus of a eukaryotic cell."),
    OrganelleLesson("Mitochondrion", "Releases usable energy from food through cellular respiration.",
        "Cells with high energy demand often contain many mitochondria."),
    OrganelleLesson("Ribosome", "Builds proteins from amino acids using genetic instructions.",
        "Ribosomes may float in cytoplasm or attach to rough endoplasmic reticulum."),
)

@Composable
fun InteractiveLessonExplorer(subjectId: String?, chapterId: String?) {
    when (explorerKind(subjectId, chapterId)) {
        ExplorerKind.FRACTIONS -> FractionExplorer()
        ExplorerKind.CELL_ORGANELLES -> CellOrganelleExplorer()
        null -> Unit
    }
}

@Composable
private fun CellOrganelleExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val lesson = organelleLessons[selected]
    val primary = MaterialTheme.colorScheme.primary
    val outline = MaterialTheme.colorScheme.outline
    val surface = MaterialTheme.colorScheme.surface
    val secondary = MaterialTheme.colorScheme.secondary
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Explore a cell", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select an organelle to highlight where it appears and connect its structure to its function.")
            Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                organelleLessons.forEachIndexed { index, item ->
                    OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (selected == index) "Selected: ${item.name}" else "Explore ${item.name}")
                    }
                }
            }
            Canvas(Modifier.fillMaxWidth().size(260.dp).semantics {
                contentDescription = "Cell diagram with ${lesson.name} highlighted"
            }) {
                val cellTop = size.height * 0.08f
                val cellSize = Size(size.width * 0.92f, size.height * 0.82f)
                drawOval(surface, topLeft = Offset(size.width * 0.04f, cellTop), size = cellSize)
                drawOval(outline, topLeft = Offset(size.width * 0.04f, cellTop), size = cellSize, style = Stroke(width = 7f))
                fun mark(index: Int, center: Offset, radius: Float, color: Color) {
                    drawCircle(color, radius, center)
                    if (selected == index) drawCircle(primary, radius + 12f, center, style = Stroke(width = 9f))
                }
                mark(0, Offset(size.width * 0.48f, size.height * 0.46f), size.minDimension * 0.15f, secondary)
                mark(1, Offset(size.width * 0.72f, size.height * 0.31f), size.minDimension * 0.07f, primary.copy(alpha = 0.65f))
                mark(1, Offset(size.width * 0.29f, size.height * 0.67f), size.minDimension * 0.07f, primary.copy(alpha = 0.65f))
                listOf(Offset(.22f, .30f), Offset(.67f, .64f), Offset(.78f, .52f), Offset(.38f, .24f)).forEach {
                    mark(2, Offset(size.width * it.x, size.height * it.y), size.minDimension * 0.018f, outline)
                }
            }
            Text(lesson.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(lesson.function)
            Text("Evidence: ${lesson.evidence}", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Exploring this diagram does not submit an answer or change mastery.", style = MaterialTheme.typography.bodySmall)
        }
    }
}
