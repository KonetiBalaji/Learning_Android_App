package com.studycompanion

import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModelProvider
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import java.io.File

/** Runs against a disposable backend at localhost:18763 on the emulator host. */
class LearningFlowTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun screenshot(name: String) {
        rule.waitForIdle()
        val directory = File(rule.activity.getExternalFilesDir(null), "qa").apply { mkdirs() }
        val image = InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        File(directory, "$name.png").outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test fun uploadFeedbackResumeResultsAndMistakeReview() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        if (model.state.value.signedIn) {
            rule.runOnIdle { model.signOut() }
            rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
        }
        screenshot("01-welcome")
        val username = "qa" + System.currentTimeMillis()
        rule.onNodeWithText("Username").performScrollTo().performTextInput(username)
        rule.onNodeWithText("Password · 10+ characters").performScrollTo().performTextInput("disposable-test-password")
        rule.onNodeWithText("Study server URL").performScrollTo().performTextClearance()
        rule.onNodeWithText("Study server URL").performTextInput("http://10.0.2.2:18763")
        rule.onNodeWithText("Create your study account").performScrollTo().performClick()
        rule.waitUntil(120_000) { model.state.value.signedIn && !model.state.value.busy }
        assertNull(model.state.value.error)
        rule.onNodeWithText("Your learning library").assertExists()
        // A refused connection must leave a readable failure and a working retry action.
        rule.runOnIdle {
            model.session.server = "http://10.0.2.2:1"
            model.refresh()
        }
        rule.waitUntil(30_000) { model.state.value.error != null && !model.state.value.busy }
        rule.onNodeWithText("Retry").assertExists()
        rule.runOnIdle { model.session.server = "http://10.0.2.2:18763" }
        rule.onNodeWithText("Retry").performScrollTo().performClick()
        rule.waitUntil(30_000) { !model.state.value.busy && model.state.value.error == null }
        val text = """
            Chapter 1 Cells
            Mitochondria produce usable energy through cellular respiration inside living cells.
            Ribosomes assemble proteins using instructions carried by messenger molecules.
            Chloroplasts capture sunlight and transform light into chemical energy.
            Membranes control the movement of substances into and outside cells.
            Chromosomes contain genetic information passed between successive generations.
            Vacuoles store water and dissolved substances within plant cells.
            Chapter 2 Ecology
            Ecosystems include organisms interacting with their surrounding physical environment.
            Populations consist of individuals belonging to the same species.
            Communities contain several populations living together in one habitat.
            Decomposers break down dead material and recycle essential nutrients.
            Producers manufacture their own food using sunlight or chemical reactions.
            Consumers obtain energy by eating producers or other living organisms.
        """.trimIndent()
        val file = File(rule.activity.cacheDir, "Biology.txt").apply { writeText(text) }
        rule.runOnIdle { model.upload(Uri.fromFile(file)) }
        rule.waitUntil(120_000) { !model.state.value.busy && model.state.value.document != null }
        assertNull(model.state.value.error)
        screenshot("02-study-selection")
        rule.onNodeWithText("Start practice").performScrollTo().performClick()
        rule.waitUntil(120_000) { model.state.value.quiz != null && !model.state.value.busy }
        assertNull(model.state.value.error)
        screenshot("03-question")
        // Select one intentionally wrong option using the exact source retained by the backend.
        for (index in 0 until 10) {
            val quiz = model.state.value.quiz!!
            val question = quiz.getJSONObject("question")
            val choices = question.getJSONArray("choices")
            val prompt = question.getString("prompt")
            // Choosing the first choice exercises either feedback state; force at least one mistake
            // by using a word absent from the actual sample's sentence context.
            val quoteStart = prompt.indexOf('“')
            val masked = prompt.substring(quoteStart + 1).removeSuffix("”")
            val correct = (0 until choices.length()).first { choice -> text.contains(masked.replace("_____", choices.getString(choice))) }
            val selected = if (index == 0) (correct + 1) % choices.length() else correct
            rule.onNodeWithText(choices.getString(selected), useUnmergedTree = false).performScrollTo().performClick()
            rule.onNodeWithText("Check answer").performScrollTo().performClick()
            rule.waitUntil(120_000) { model.state.value.quiz?.optJSONObject("feedback") != null && !model.state.value.busy }
            assertNull(model.state.value.error)
            assertEquals(index != 0, model.state.value.quiz!!.getJSONObject("feedback").getBoolean("correct"))
            if (index == 0) {
                screenshot("04-teaching-feedback")
                rule.onNodeWithText("Read source passage").performScrollTo().performClick()
                rule.waitUntil(30_000) { model.state.value.source != null && !model.state.value.busy }
                rule.onNodeWithText("Source passage").assertExists()
                screenshot("05-source-passage")
                rule.onNodeWithText("Close").performClick()
                rule.activityRule.scenario.recreate()
                rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
                assertNotNull(model.state.value.quiz!!.optJSONObject("feedback"))
            }
            rule.onNodeWithText(if (index == 9) "See my results" else "Next question").performScrollTo().performClick()
            rule.waitUntil(120_000) { !model.state.value.busy && (model.state.value.quiz!!.getInt("index") == index + 1) }
            assertNull(model.state.value.error)
        }
        rule.onNodeWithText("90%").assertExists()
        screenshot("06-results")
        rule.onNodeWithText("Review mistakes").performScrollTo().performClick()
        rule.onNodeWithText("Learn from the tricky ones").assertExists()
        screenshot("07-mistake-review")
        rule.onNodeWithText("Retry incorrect questions").performScrollTo().performClick()
        rule.waitUntil(120_000) { model.state.value.screen == "quiz" && !model.state.value.busy }
        assertEquals(1, model.state.value.quiz!!.getInt("count"))
        // Leave server history disposable and remove this test account after verification.
        rule.runOnIdle { model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
    }
}
