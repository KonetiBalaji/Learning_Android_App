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
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class MatterState(val name: String, val spacing: String, val movement: String)
val matterStates = listOf(
    MatterState("Solid", "closely packed in an ordered pattern", "vibrate around fixed positions"),
    MatterState("Liquid", "close together without a fixed pattern", "move past one another"),
    MatterState("Gas", "far apart", "move freely in all directions"),
)

data class MotionModel(val speedMetresPerSecond: Int, val seconds: Int) {
    init { require(speedMetresPerSecond > 0 && seconds > 0) }
    val distanceMetres: Int get() = speedMetresPerSecond * seconds
}
val motionModels = listOf(MotionModel(2, 3), MotionModel(3, 4), MotionModel(5, 5))

data class EnergyLevel(val organism: String, val role: String, val energyUnits: Int)
val ecosystemEnergyLevels = listOf(
    EnergyLevel("Grass", "Producer", 10_000),
    EnergyLevel("Grasshopper", "Primary consumer", 1_000),
    EnergyLevel("Frog", "Secondary consumer", 100),
    EnergyLevel("Snake", "Tertiary consumer", 10),
)

@Composable
fun MatterParticleExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val state = matterStates[selected]
    val particle = MaterialTheme.colorScheme.primary
    val outline = MaterialTheme.colorScheme.outline
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Explore particle models", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select a state of matter to compare particle spacing and movement.")
            matterStates.forEachIndexed { index, item ->
                OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (selected == index) "Selected: ${item.name}" else item.name)
                }
            }
            Canvas(Modifier.fillMaxWidth().size(240.dp).semantics {
                contentDescription = "${state.name} particle model: particles are ${state.spacing} and ${state.movement}"
            }) {
                drawRect(outline, style = Stroke(width = 5f))
                val points = when (selected) {
                    0 -> (0 until 4).flatMap { row -> (0 until 4).map { col -> Offset(.2f + col * .2f, .2f + row * .2f) } }
                    1 -> listOf(.18f to .22f, .38f to .18f, .61f to .25f, .80f to .17f, .25f to .46f, .49f to .41f, .73f to .48f, .15f to .72f, .41f to .69f, .65f to .75f, .84f to .65f)
                        .map { Offset(it.first, it.second) }
                    else -> listOf(.16f to .20f, .76f to .15f, .43f to .48f, .85f to .73f, .19f to .82f)
                        .map { Offset(it.first, it.second) }
                }
                points.forEach { drawCircle(particle, size.minDimension * .035f, Offset(size.width * it.x, size.height * it.y)) }
            }
            Text("${state.name}: ${state.spacing}; particles ${state.movement}.", fontWeight = FontWeight.Bold)
            NonSubmissionNotice("particle model")
        }
    }
}

@Composable
fun ConstantSpeedExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val model = motionModels[selected]
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Explore constant speed", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select a speed and time to see distance = speed × time.")
            motionModels.forEachIndexed { index, item ->
                OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                    val label = "${item.speedMetresPerSecond} m/s for ${item.seconds} s"
                    Text(if (selected == index) "Selected: $label" else label)
                }
            }
            Text("${model.speedMetresPerSecond} m/s × ${model.seconds} s = ${model.distanceMetres} m",
                style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold,
                modifier = Modifier.semantics { contentDescription =
                    "${model.speedMetresPerSecond} metres per second for ${model.seconds} seconds gives ${model.distanceMetres} metres" })
            Text("At constant speed, equal time intervals add equal distances.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            NonSubmissionNotice("motion model")
        }
    }
}

@Composable
fun EcosystemEnergyExplorer() {
    var selected by rememberSaveable { mutableIntStateOf(0) }
    val level = ecosystemEnergyLevels[selected]
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant), modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Trace ecosystem energy", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Select each level in this simplified food chain. The model uses a 10% transfer example.")
            ecosystemEnergyLevels.forEachIndexed { index, item ->
                OutlinedButton(onClick = { selected = index }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (selected == index) "Selected: ${item.organism}" else "${item.organism} →")
                }
            }
            Text("${level.organism}: ${level.role}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("Example energy available: ${level.energyUnits} units", modifier = Modifier.semantics {
                contentDescription = "${level.organism}, ${level.role}, ${level.energyUnits} example energy units"
            })
            Text("Energy decreases between trophic levels because organisms use energy and release much of it as heat.",
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            NonSubmissionNotice("energy model")
        }
    }
}

@Composable
private fun NonSubmissionNotice(name: String) {
    Text("Exploring the $name does not submit an answer or change mastery.", style = MaterialTheme.typography.bodySmall)
}
