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

/** Disposable local backend at 18763 plus simulated-outage fixture at 18764; see provider-fallback.md. */
class LearningFlowTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    @Test fun unavailableAiClearlyOffersEasyLocalPractice() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        if (model.state.value.signedIn) {
            rule.runOnIdle { model.signOut() }
            rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
        }
        rule.onNodeWithText("Username").performScrollTo().performTextInput("fallback" + System.currentTimeMillis())
        rule.onNodeWithText("Password · 10+ characters").performScrollTo().performTextInput("disposable-fallback-password")
        rule.onNodeWithText("Study server URL").performScrollTo().performTextClearance()
        rule.onNodeWithText("Study server URL").performTextInput("http://10.0.2.2:18764")
        rule.onNodeWithText("Create your study account").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.signedIn && !model.state.value.busy }
        val file = File(rule.activity.cacheDir, "fallback.txt").apply { writeText("""
            Chapter 1 Cells
            Mitochondria produce usable energy through cellular respiration inside living cells.
            Ribosomes assemble proteins using instructions carried by messenger molecules.
        """.trimIndent()) }
        rule.runOnIdle { model.upload(Uri.fromFile(file)) }
        rule.waitUntil(30_000) { model.state.value.document != null && !model.state.value.busy }
        assertNull(model.state.value.error)
        // Request Hard through the normal ViewModel; the server must truthfully return Easy.
        rule.runOnIdle { model.startQuiz(emptySet(), 1, "multiple_choice", "hard", "", "", "") }
        rule.waitUntil(30_000) { model.state.value.quiz != null && !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals("local_practice", model.state.value.quiz!!.getString("mode"))
        assertEquals("easy", model.state.value.quiz!!.getJSONObject("question").getString("difficulty"))
        rule.onNodeWithText("Local fallback practice").assertExists()
        rule.onNodeWithText("AI is unavailable. This quiz uses local passage recall at Easy difficulty, rather than the requested AI difficulty.").assertExists()
        rule.runOnIdle { model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
    }

    private fun screenshot(name: String) {
        rule.waitForIdle()
        val directory = File(rule.activity.getExternalFilesDir(null), "qa").apply { mkdirs() }
        val image = InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot()
        File(directory, "$name.png").outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test fun reviewUncertainScannedPdfBeforePractice() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        if (model.state.value.signedIn) {
            rule.runOnIdle { model.signOut() }
            rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
        }
        val text = """
            Chapter 1 Cells
            Mitochondria produce usable energy through cellular respiration inside living cells.
            Ribosomes assemble proteins using instructions carried by messenger molecules.
            Chloroplasts capture sunlight and transform light into chemical energy.
            Membranes control the movement of substances into and outside cells.
            Chromosomes contain genetic information passed between successive generations.
            Vacuoles store water and dissolved substances within plant cells.
        """.trimIndent()
        val username = "ocr" + System.currentTimeMillis()
        rule.onNodeWithText("Username").performScrollTo().performTextInput(username)
        rule.onNodeWithText("Password · 10+ characters").performScrollTo().performTextInput("disposable-scan-password")
        rule.onNodeWithText("Study server URL").performScrollTo().performTextClearance()
        rule.onNodeWithText("Study server URL").performTextInput("http://10.0.2.2:18763")
        rule.onNodeWithText("Create your study account").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.signedIn && !model.state.value.busy }
        val file = File(rule.activity.cacheDir, "OCR-biology.pdf")
        val image = android.graphics.Bitmap.createBitmap(1800, 1100, android.graphics.Bitmap.Config.ARGB_8888)
        val canvas = android.graphics.Canvas(image)
        canvas.drawColor(android.graphics.Color.WHITE)
        val paint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply { color = android.graphics.Color.BLACK; textSize = 32f }
        text.lines().forEachIndexed { index, line -> canvas.drawText(line, 40f, 70f + index * 100f, paint) }
        val pdf = android.graphics.pdf.PdfDocument()
        val page = pdf.startPage(android.graphics.pdf.PdfDocument.PageInfo.Builder(1800, 1100, 1).create())
        page.canvas.drawBitmap(image, 0f, 0f, null)
        pdf.finishPage(page)
        file.outputStream().use(pdf::writeTo)
        pdf.close()
        image.recycle()
        rule.runOnIdle { model.upload(Uri.fromFile(file)) }
        rule.waitUntil(200_000) { !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals("needs_review", model.state.value.document!!.getString("processing_state"))
        rule.onNodeWithText("Start practice").assertDoesNotExist()
        rule.onNodeWithText("Review scanned text").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.ocrPage != null && !model.state.value.busy }
        rule.onNodeWithContentDescription("Original scanned page 1").assertExists()
        screenshot("09-ocr-review")
        rule.onNodeWithText("Transcription — correct unclear words").performScrollTo().performTextClearance()
        rule.onNodeWithText("Transcription — correct unclear words").performTextInput(text)
        rule.onNodeWithText("Confirm transcription matches page").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "configure" && !model.state.value.busy }
        assertEquals("ready", model.state.value.document!!.getString("processing_state"))
        rule.onNodeWithText("Questions · 1–50").performScrollTo().performTextClearance()
        rule.onNodeWithText("Questions · 1–50").performTextInput("5")
        rule.onNodeWithText("Start practice").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "quiz" && !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals(1, model.state.value.quiz!!.getJSONObject("question").getInt("page"))
        rule.runOnIdle { model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
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
        rule.onNodeWithText("Explore selected material with semantic search").performScrollTo().performClick()
        rule.onNodeWithText("What do you want to understand?").performScrollTo().performTextInput("cell power factory")
        rule.onNodeWithText("Find source passages").performScrollTo().performClick()
        rule.waitUntil(120_000) { model.state.value.searchHits != null && !model.state.value.busy }
        assertNull(model.state.value.error)
        assertTrue(model.state.value.searchHits!!.first().getString("quote").contains("Mitochondria"))
        screenshot("10-semantic-search")
        rule.onNodeWithText("Back to document").performScrollTo().performClick()
        rule.onNodeWithText("Ask the document tutor").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "tutor" && !model.state.value.busy }
        rule.onNodeWithText("Question for the tutor").performScrollTo().performTextInput("cell power factory")
        rule.onNodeWithText("Ask from selected material").performScrollTo().performClick()
        rule.waitUntil(120_000) { model.state.value.tutorTurns.size == 1 && !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals("source_excerpt", model.state.value.tutorTurns.first().getString("mode"))
        assertTrue(model.state.value.tutorTurns.first().getString("answer").contains("Mitochondria"))
        rule.onNodeWithText("Read cited source").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.source != null && !model.state.value.busy }
        rule.onNodeWithText("Close").performClick()
        screenshot("11-document-tutor")
        rule.onNodeWithText("Back to document").performScrollTo().performClick()
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
        val completedQuiz = model.state.value.quiz!!.getString("id")
        rule.onNodeWithText("Plan my next practice focus").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "adaptive" && !model.state.value.busy }
        val advice = model.state.value.recommendation!!
        rule.onNodeWithText("Start focused practice").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "quiz" && !model.state.value.busy }
        assertNotEquals(completedQuiz, model.state.value.quiz!!.getString("id"))
        assertEquals(advice.getInt("count"), model.state.value.quiz!!.getInt("count"))
        assertEquals(advice.getJSONArray("section_ids").getString(0), model.state.value.quiz!!.getJSONObject("question").getString("section_id"))
        rule.onNodeWithText("Progress", substring = false).performClick()
        rule.onNodeWithText("9 / 10 · 90%").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "results" && !model.state.value.busy }
        assertEquals(completedQuiz, model.state.value.quiz!!.getString("id"))
        rule.onNodeWithText("Create flashcards for spaced review").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "flashcards" && !model.state.value.busy }
        assertEquals(10, model.state.value.flashcards.size)
        rule.onNodeWithText("Reveal answer").performScrollTo().performClick()
        screenshot("08-spaced-review")
        rule.onNodeWithText("Good — after a pause").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.flashcards.size == 9 && !model.state.value.busy }
        rule.onNodeWithText("Back to results").performScrollTo().performClick()
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
