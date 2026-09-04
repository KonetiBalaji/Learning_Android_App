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
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp

enum class ExplorerKind { FRACTIONS, CELL_ORGANELLES, SENTENCE_PARTS, MAP_COORDINATES }

fun explorerKind(subjectId: String?, chapterId: String?): ExplorerKind? = when {
    subjectId == "math" && chapterId == "fractions" -> ExplorerKind.FRACTIONS
    subjectId == "science" && chapterId == "cells" -> ExplorerKind.CELL_ORGANELLES
    subjectId == "english" && chapterId == "grammar" -> ExplorerKind.SENTENCE_PARTS
    subjectId == "social" && chapterId == "geography" -> ExplorerKind.MAP_COORDINATES
    else -> null
}

data class OrganelleLesson(val name: String, val function: String, val evidence: String)
data class SentencePartLesson(val name: String, val words: String, val role: String, val check: String)
data class MapLineLesson(val name: String, val value: String, val role: String, val check: String)

val organelleLessons = listOf(
    OrganelleLesson("Nucleus", "Stores most of the cell's DNA and helps direct cell activities.",
        "Chromosomes are kept inside the nucleus of a eukaryotic cell."),
    OrganelleLesson("Mitochondrion", "Releases usable energy from food through cellular respiration.",
        "Cells with high energy demand often contain many mitochondria."),
    OrganelleLesson("Ribosome", "Builds proteins from amino acids using genetic instructions.",
        "Ribosomes may float in cytoplasm or attach to rough endoplasmic reticulum."),
)

val sentencePartLessons = listOf(
    SentencePartLesson("Subject", "The curious student", "Names who or what performs the action.",
        "Ask: Who solved something? The curious student."),
    SentencePartLesson("Verb", "solved", "Expresses the action performed by the subject.",
        "Ask: What did the student do? Solved."),
    SentencePartLesson("Object", "the puzzle", "Receives the action expressed by the verb.",
        "Ask: What did the student solve? The puzzle."),
)

val mapLineLessons = listOf(
    MapLineLesson("Equator", "0° latitude", "Runs east-west and divides Earth into Northern and Southern Hemispheres.",
        "Latitude measures distance north or south of the Equator."),
    MapLineLesson("Prime Meridian", "0° longitude", "Runs north-south and divides Earth into Eastern and Western Hemispheres.",
        "Longitude measures distance east or west of the Prime Meridian."),
    MapLineLesson("Coordinates", "20° N, 60° E", "Combine latitude first and longitude second to identify one location.",
        "20° N is north of the Equator; 60° E is east of the Prime Meridian."),
)

@Composable
fun InteractiveLessonExplorer(subjectId: String?, chapterId: String?) {
    when (explorerKind(subjectId, chapterId)) {
        ExplorerKind.FRACTIONS -> FractionExplorer()
        ExplorerKind.CELL_ORGANELLES -> CellOrganelleExplorer()
        ExplorerKind.SENTENCE_PARTS -> SentencePartExplorer()
        ExplorerKind.MAP_COORDINATES -> MapCoordinateExplorer()
        null -> Unit
    }
}

@Composable
private fun MapCoordinateExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val lesson = mapLineLessons[selected]
    val primary = MaterialTheme.colorScheme.primary
    val outline = MaterialTheme.colorScheme.outline
    val surface = MaterialTheme.colorScheme.surface
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Explore map coordinates", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select a reference to highlight how latitude and longitude locate places on Earth.")
            Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                mapLineLessons.forEachIndexed { index, item ->
                    OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (selected == index) "Selected: ${item.name}" else "Explore ${item.name}")
                    }
                }
            }
            Canvas(Modifier.fillMaxWidth().size(250.dp).semantics {
                contentDescription = "Globe diagram with ${lesson.name} highlighted"
            }) {
                val center = Offset(size.width / 2f, size.height / 2f)
                val radius = size.minDimension * .39f
                drawCircle(surface, radius, center)
                drawCircle(outline, radius, center, style = Stroke(width = 7f))
                val equatorColor = if (selected == 0 || selected == 2) primary else outline.copy(alpha = .45f)
                val meridianColor = if (selected == 1 || selected == 2) primary else outline.copy(alpha = .45f)
                drawLine(equatorColor, Offset(center.x - radius, center.y), Offset(center.x + radius, center.y), strokeWidth = if (selected == 0) 12f else 7f)
                drawLine(meridianColor, Offset(center.x, center.y - radius), Offset(center.x, center.y + radius), strokeWidth = if (selected == 1) 12f else 7f)
                drawOval(outline.copy(alpha = .35f), Offset(center.x - radius * .45f, center.y - radius),
                    Size(radius * .9f, radius * 2f), style = Stroke(width = 4f))
                if (selected == 2) {
                    val point = Offset(center.x + radius * .55f, center.y - radius * .34f)
                    drawCircle(primary, 15f, point)
                    drawCircle(surface, 6f, point)
                }
            }
            Text("${lesson.name}: ${lesson.value}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(lesson.role)
            Text(lesson.check, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Exploring this globe does not submit an answer or change mastery.", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun SentencePartExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val lesson = sentencePartLessons[selected]
    val highlight = MaterialTheme.colorScheme.secondaryContainer
    val highlightedSentence = buildAnnotatedString {
        sentencePartLessons.forEachIndexed { index, part ->
            if (index > 0) append(" ")
            withStyle(SpanStyle(background = if (index == selected) highlight else Color.Transparent,
                fontWeight = if (index == selected) FontWeight.Bold else FontWeight.Normal)) {
                append(part.words)
            }
        }
        append(".")
    }
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Build a sentence", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select a sentence part to highlight its words and discover the job it performs.")
            Text(highlightedSentence, style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.fillMaxWidth().semantics { contentDescription =
                    "Sentence with ${lesson.name} highlighted: ${lesson.words}" })
            Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                sentencePartLessons.forEachIndexed { index, part ->
                    OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                        Text(if (selected == index) "Selected: ${part.name}" else "Explore ${part.name}")
                    }
                }
            }
            Text("${lesson.name}: ${lesson.words}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(lesson.role)
            Text(lesson.check, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Exploring this sentence does not submit an answer or change mastery.", style = MaterialTheme.typography.bodySmall)
        }
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
