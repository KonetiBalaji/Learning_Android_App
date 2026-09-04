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

data class HistoricalSource(val source: String, val classification: String, val reasoning: String, val limitation: String)
val historicalSources = listOf(
    HistoricalSource("A participant's diary written during an event", "Primary source",
        "It was created by a participant at the time being studied.", "One participant may have a limited or biased viewpoint."),
    HistoricalSource("A photograph taken at the event", "Primary source",
        "It records a moment during the event.", "It shows only what was inside the frame and needs context."),
    HistoricalSource("A textbook chapter published decades later", "Secondary source",
        "It interprets earlier evidence after the event.", "Its account depends on the evidence and interpretations its author selected."),
)

data class CivicStage(val name: String, val purpose: String)
val civicStages = listOf(
    CivicStage("Proposal", "Describe the shared problem and a possible response."),
    CivicStage("Public input", "Gather evidence and hear affected perspectives."),
    CivicStage("Decision", "Use the authorized process to accept, revise or reject the proposal."),
    CivicStage("Implementation and review", "Carry out the decision, observe results and review it through lawful channels."),
)

enum class MarketState(val label: String) { SHORTAGE("Shortage"), BALANCED("Quantity supplied equals quantity demanded"), SURPLUS("Surplus") }
data class MarketExample(val price: Int, val quantityDemanded: Int, val quantitySupplied: Int) {
    init { require(price > 0 && quantityDemanded >= 0 && quantitySupplied >= 0) }
    val state: MarketState get() = when {
        quantityDemanded > quantitySupplied -> MarketState.SHORTAGE
        quantityDemanded < quantitySupplied -> MarketState.SURPLUS
        else -> MarketState.BALANCED
    }
    val difference: Int get() = kotlin.math.abs(quantityDemanded - quantitySupplied)
}
val marketExamples = listOf(
    MarketExample(2, 12, 4),
    MarketExample(4, 8, 8),
    MarketExample(6, 4, 12),
)

@Composable
fun HistoricalSourcesExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val source = historicalSources[selected]
    SocialCard("Evaluate historical sources", "Select a source to distinguish its type, value and limitation.") {
        historicalSources.forEachIndexed { index, item ->
            SocialSelection(selected == index, item.source) { selected = index }
        }
        Text(source.classification, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(source.reasoning)
        Text("Limitation: ${source.limitation}", color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.semantics { contentDescription = "${source.classification}. ${source.reasoning} Limitation. ${source.limitation}" })
        SocialNotice("source analysis")
    }
}

@Composable
fun CivicProcessExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val stage = civicStages[selected]
    SocialCard("Trace a civic decision", "Explore a general democratic decision model. Exact legal processes vary by jurisdiction.") {
        civicStages.forEachIndexed { index, item ->
            SocialSelection(selected == index, "${index + 1}. ${item.name}") { selected = index }
        }
        Text(stage.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(stage.purpose, modifier = Modifier.semantics { contentDescription = "Civic stage ${selected + 1}, ${stage.name}. ${stage.purpose}" })
        Text("This is an illustrative sequence, not legal advice or a claim about one country's government.",
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        SocialNotice("civic process")
    }
}

@Composable
fun MarketBalanceExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val example = marketExamples[selected]
    SocialCard("Explore supply and demand", "Select a hypothetical price and compare quantities in this simplified market.") {
        marketExamples.forEachIndexed { index, item ->
            SocialSelection(selected == index, "Price ${item.price}") { selected = index }
        }
        Text("Demanded: ${example.quantityDemanded}   Supplied: ${example.quantitySupplied}",
            style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold,
            modifier = Modifier.semantics { contentDescription =
                "At price ${example.price}, quantity demanded is ${example.quantityDemanded} and quantity supplied is ${example.quantitySupplied}" })
        Text(example.state.label)
        if (example.state != MarketState.BALANCED) Text("Difference: ${example.difference} units")
        Text("This table is a teaching example; real markets have additional influences.",
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        SocialNotice("market model")
    }
}

@Composable
private fun SocialCard(title: String, instruction: String, content: @Composable () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(instruction)
            content()
        }
    }
}

@Composable
private fun SocialSelection(selected: Boolean, label: String, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Text(if (selected) "Selected: $label" else label)
    }
}

@Composable
private fun SocialNotice(name: String) {
    Text("Exploring the $name does not submit an answer or change mastery.", style = MaterialTheme.typography.bodySmall)
}
