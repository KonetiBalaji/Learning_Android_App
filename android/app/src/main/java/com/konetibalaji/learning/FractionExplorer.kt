package com.konetibalaji.learning

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt

@Composable
fun FractionExplorer() {
    var denominator by rememberSaveable { mutableIntStateOf(4) }
    var left by rememberSaveable { mutableIntStateOf(3) }
    var right by rememberSaveable { mutableIntStateOf(1) }
    val model = FractionModel(denominator, left, right)
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Explore equal-sized parts", style = MaterialTheme.typography.titleLarge)
            Text("Both bars represent the same-sized whole. Change the number of equal parts, then add the selected parts.")
            Text("Equal parts in each whole: $denominator")
            Slider(value = denominator.toFloat(), onValueChange = {
                val changed = model.withDenominator(it.roundToInt())
                denominator = changed.denominator; left = changed.left; right = changed.right
            }, valueRange = 2f..12f, steps = 9, modifier = Modifier.semantics { contentDescription = "Equal parts per whole" })
            Text("First fraction: $left/$denominator")
            FractionBar(left, denominator, "First fraction")
            Slider(value = left.toFloat(), onValueChange = { left = it.roundToInt() }, valueRange = 0f..denominator.toFloat(), steps = denominator - 1,
                modifier = Modifier.semantics { contentDescription = "First numerator" })
            Text("Second fraction: $right/$denominator")
            FractionBar(right, denominator, "Second fraction")
            Slider(value = right.toFloat(), onValueChange = { right = it.roundToInt() }, valueRange = 0f..denominator.toFloat(), steps = denominator - 1,
                modifier = Modifier.semantics { contentDescription = "Second numerator" })
            Text("$left/$denominator + $right/$denominator = ${model.numerator}/$denominator = ${model.simplified}", style = MaterialTheme.typography.titleMedium)
            FractionBar(model.numerator.coerceAtMost(denominator), denominator, "Sum, first whole")
            if (model.numerator > denominator) FractionBar(model.numerator - denominator, denominator, "Sum, second whole")
            Text("${model.wholeParts} whole(s) and ${model.remainder}/$denominator remaining. Add the numerators because the parts are the same size; keep the denominator.")
            Text("Exploring this model does not submit an answer or change your mastery score.", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { denominator = 4; left = 3; right = 1 }) { Text("Reset fraction model") }
        }
    }
}

@Composable
private fun FractionBar(filled: Int, parts: Int, label: String) {
    Row(Modifier.fillMaxWidth().height(28.dp).semantics(mergeDescendants = true) {
        contentDescription = "$label: $filled selected out of $parts equal parts"
    }, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
        repeat(parts) { index ->
            Box(Modifier.weight(1f).fillMaxHeight().background(
                if (index < filled) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                RoundedCornerShape(2.dp)))
        }
    }
}
