package com.konetibalaji.learning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class ReadingEvidenceStep(val label: String, val text: String)
val readingPassage = "After weeks without rain, the garden soil was cracked. Maya carried two full watering cans outside before breakfast."
val readingEvidenceSteps = listOf(
    ReadingEvidenceStep("Text detail", "The soil was cracked after weeks without rain."),
    ReadingEvidenceStep("Inference", "Maya intends to water the dry garden."),
    ReadingEvidenceStep("Supporting evidence", "She carried two full watering cans outside."),
)

data class WordPart(val label: String, val text: String, val meaning: String)
val wordParts = listOf(
    WordPart("Prefix", "un-", "not"),
    WordPart("Root", "help", "to assist"),
    WordPart("Suffix", "-ful", "full of or characterized by"),
)

data class ParagraphPart(val label: String, val sentence: String, val purpose: String)
val paragraphParts = listOf(
    ParagraphPart("Topic sentence", "School gardens make science lessons more concrete.", "States the paragraph's main claim."),
    ParagraphPart("Evidence", "Students can measure real plant growth each week.", "Provides a relevant observable example."),
    ParagraphPart("Explanation", "These measurements connect classroom graphs to living organisms.", "Explains how the evidence supports the claim."),
    ParagraphPart("Concluding sentence", "For this reason, a garden can become an effective outdoor laboratory.", "Restates the idea and closes the paragraph."),
)

@Composable
fun ReadingEvidenceExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val step = readingEvidenceSteps[selected]
    ExplorerCard("Build an inference", "Connect a text detail to a supported inference.") {
        Text(readingPassage, style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.semantics { contentDescription = "Reading passage. $readingPassage" })
        readingEvidenceSteps.forEachIndexed { index, item ->
            SelectionButton(selected == index, item.label) { selected = index }
        }
        Text(step.label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(step.text)
        Text("An inference must be supported by the passage; it is not a guess without evidence.",
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        EnglishNonSubmissionNotice("reading evidence")
    }
}

@Composable
fun WordPartsExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val part = wordParts[selected]
    ExplorerCard("Build word meaning", "Select a part of unhelpful to see how it contributes meaning.") {
        Text("un + help + ful", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold,
            modifier = Modifier.semantics { contentDescription = "Word unhelpful split into prefix un, root help, and suffix ful" })
        wordParts.forEachIndexed { index, item ->
            SelectionButton(selected == index, "${item.label}: ${item.text}") { selected = index }
        }
        Text("${part.text} means ${part.meaning}", style = MaterialTheme.typography.titleMedium)
        Text("Together, unhelpful means not providing help.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        EnglishNonSubmissionNotice("word model")
    }
}

@Composable
fun ParagraphStructureExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val part = paragraphParts[selected]
    ExplorerCard("Explore paragraph structure", "Select each sentence to see its job in a reasoned paragraph.") {
        paragraphParts.forEachIndexed { index, item ->
            SelectionButton(selected == index, item.label) { selected = index }
        }
        Text(part.label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(part.sentence, modifier = Modifier.semantics {
            contentDescription = "${part.label}. ${part.sentence}. ${part.purpose}"
        })
        Text(part.purpose, color = MaterialTheme.colorScheme.onSurfaceVariant)
        EnglishNonSubmissionNotice("paragraph model")
    }
}

@Composable
private fun ExplorerCard(title: String, instruction: String, content: @Composable () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(instruction)
            content()
        }
    }
}

@Composable
private fun SelectionButton(selected: Boolean, label: String, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Text(if (selected) "Selected: $label" else label)
    }
}

@Composable
private fun EnglishNonSubmissionNotice(name: String) {
    Text("Exploring the $name does not submit an answer or change mastery.", style = MaterialTheme.typography.bodySmall)
}
