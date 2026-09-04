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

data class AlgebraBalanceStep(
    val operation: String,
    val left: String,
    val right: String,
    val reason: String,
)

val algebraBalanceSteps = listOf(
    AlgebraBalanceStep("Start", "2x + 3", "11", "The equal sign says both sides have the same value."),
    AlgebraBalanceStep("Subtract 3 from both sides", "2x", "8", "Applying the same subtraction to both sides keeps them equal."),
    AlgebraBalanceStep("Divide both sides by 2", "x", "4", "Dividing both equal sides by the same nonzero number keeps them equal."),
    AlgebraBalanceStep("Check x = 4", "2 × 4 + 3", "11", "The left side becomes 8 + 3 = 11, so x = 4 satisfies the original equation."),
)

@Composable
fun AlgebraBalanceExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val step = algebraBalanceSteps[selected]
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Balance an equation", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Move through legal operations on 2x + 3 = 11. Every change must preserve equality.")
            algebraBalanceSteps.forEachIndexed { index, item ->
                OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (selected == index) "Selected: ${item.operation}" else item.operation)
                }
            }
            Text("${step.left}  =  ${step.right}", style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth().semantics {
                    contentDescription = "${step.left} equals ${step.right}"
                })
            Text(step.reason, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("Exploring equation steps does not submit an answer or change mastery.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
}
