package com.studycompanion

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.studycompanion.data.objects

@Composable
fun ProgressSharingScreen(state: StudyState, model: StudyViewModel) {
    val report = state.progressReport
    if (report != null) {
        Text("Student progress", style = MaterialTheme.typography.headlineSmall)
        val week = report.getJSONObject("week")
        Text("Last 7 days: ${week.getInt("chapters_active")} active chapters · ${week.getInt("chapters_mastered")} mastered")
        report.getJSONArray("subjects").objects().forEach { subject ->
            val mastered = subject.getInt("mastered")
            val available = subject.getInt("available")
            Text("Grade ${subject.getInt("grade")} · ${subject.getString("subject")} · $mastered/$available mastered")
            LinearProgressIndicator(progress = { mastered.toFloat() / available }, modifier = Modifier.fillMaxWidth())
        }
        report.optJSONObject("readiness")?.let { result ->
            Text("Grade 6 Mathematics readiness check", style = MaterialTheme.typography.titleMedium)
            Text("${result.getInt("correct")} / ${result.getInt("total")} correct")
            ReadinessBreakdown(result.getJSONObject("by_chapter"))
        }
        Text("Areas to practice", style = MaterialTheme.typography.titleMedium)
        val weak = report.getJSONArray("weak_areas").objects()
        if (weak.isEmpty()) Text("No areas flagged in the available lesson evidence.")
        weak.forEach { Text("Grade ${it.getInt("grade")} · ${it.getString("title")}") }
        Text(report.getString("recommendation"))
        TextButton(onClick = model::showProgressSharing, enabled = !state.busy) { Text("Back to shared reports") }
        return
    }

    var code by remember { mutableStateOf("") }
    var revoke by remember { mutableStateOf<String?>(null) }
    Text("Teacher and parent reports", style = MaterialTheme.typography.headlineSmall)
    Text("Share only your curriculum progress. Give the invitation privately to the person you choose. It expires after 15 minutes and can be used once.")
    listOf("teacher", "parent").forEach { role ->
        OutlinedButton(onClick = { model.inviteProgressViewer(role) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
            Text("Invite a $role")
        }
        if (state.progressInvite?.optString("role") != role) {
            TextButton(onClick = { model.cancelProgressInvite(role) }, enabled = !state.busy) {
                Text("Cancel unused $role invitation")
            }
        }
    }
    state.progressInvite?.let { invite ->
        Text("Private ${invite.getString("role")} invitation")
        SelectionContainer { Text(invite.getString("code")) }
        TextButton(onClick = { model.cancelProgressInvite(invite.getString("role")) }, enabled = !state.busy) {
            Text("Cancel this invitation")
        }
    }
    OutlinedTextField(code, { if (it.length <= 64) code = it }, label = { Text("Invitation code") },
        enabled = !state.busy, singleLine = true, modifier = Modifier.fillMaxWidth())
    Button(onClick = { model.redeemProgressInvite(code.trim()); code = "" },
        enabled = !state.busy && code.trim().length == 32, modifier = Modifier.fillMaxWidth()) {
        Text("Accept invitation")
    }
    if (state.progressLinks.isEmpty()) Text("No active sharing links.")
    state.progressLinks.forEachIndexed { index, link ->
        val id = link.getString("id")
        val role = link.getString("role")
        if (link.getString("direction") == "received") {
            OutlinedButton(onClick = { model.readSharedProgress(id) }, enabled = !state.busy,
                modifier = Modifier.fillMaxWidth()) { Text("Open $role report ${index + 1}") }
        } else Text("Shared with a $role · link ${index + 1}")
        TextButton(onClick = { revoke = id }, enabled = !state.busy) { Text("Remove link ${index + 1}") }
    }
    revoke?.let { id ->
        AlertDialog(onDismissRequest = { revoke = null }, title = { Text("Remove this sharing link?") },
            text = { Text("The viewer will lose access to this student's report.") },
            confirmButton = { TextButton(onClick = { revoke = null; model.revokeProgressLink(id) }) { Text("Remove access") } },
            dismissButton = { TextButton(onClick = { revoke = null }) { Text("Keep link") } })
    }
    TextButton(onClick = { model.navigate("progress") }, enabled = !state.busy) { Text("Back to progress") }
}
