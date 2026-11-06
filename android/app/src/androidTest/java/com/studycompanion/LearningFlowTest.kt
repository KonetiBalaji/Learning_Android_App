package com.studycompanion

import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelProvider
import androidx.test.platform.app.InstrumentationRegistry
import com.studycompanion.data.OfflineCache
import com.studycompanion.data.SessionStore
import com.studycompanion.data.StudyRepository
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/** Disposable local backend at 18763 plus simulated-outage fixture at 18764; see provider-fallback.md. */
class LearningFlowTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun fixtureUrl(port: Int): String {
        val host = InstrumentationRegistry.getArguments().getString("studyHost", if (android.os.Build.MODEL.contains("sdk")) "10.0.2.2" else "127.0.0.1")
        return "http://$host:$port"
    }

    private val studyServer get() =
        fixtureUrl(InstrumentationRegistry.getArguments().getString("studyPort", "18763").toInt())

    @Test fun invitedParentCanOpenOnlyTheSharedCurriculumReport() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        check(!model.state.value.signedIn) { "Run this test on a signed-out disposable installation." }
        val student = "sharestudent" + System.currentTimeMillis()
        val password = "disposable-sharing-password"
        val server = InstrumentationRegistry.getArguments().getString("sharingPort")?.let { fixtureUrl(it.toInt()) }
            ?: studyServer

        fun waitUntilIdle() = rule.waitUntil(30_000) { !model.state.value.busy }
        fun tap(label: String) = rule.onNodeWithText(label, substring = false).performScrollTo().performClick()
        fun openReports() {
            rule.onNodeWithText("Progress", substring = false).performClick()
            tap("Teacher and parent reports")
            rule.waitUntil(30_000) { model.state.value.screen == "progress-sharing" && !model.state.value.busy }
        }

        try {
            rule.runOnIdle { model.authenticate(student, password, true, server) }
            waitUntilIdle()
            assertTrue(model.state.value.signedIn)
            rule.runOnIdle { model.showCurriculum() }
            waitUntilIdle()
            rule.runOnIdle { model.openCurriculumChapter("fractions") }
            rule.waitUntil(30_000) { model.state.value.curriculumLesson != null && !model.state.value.busy }
            openReports()
            tap("Invite a parent")
            rule.waitUntil(30_000) { model.state.value.progressInvite != null && !model.state.value.busy }
            val code = model.state.value.progressInvite!!.getString("code")
            rule.runOnIdle { model.signOut() }
            waitUntilIdle()
            assertNull(model.state.value.progressInvite)
            signInForRegression(model, "shareviewer", server)
            openReports()
            rule.onNodeWithText("Invitation code").performScrollTo().performTextReplacement(code)
            tap("Accept invitation")
            rule.waitUntil(30_000) { model.state.value.progressLinks.size == 1 && !model.state.value.busy }
            tap("Open parent report 1")
            rule.waitUntil(30_000) { model.state.value.progressReport != null && !model.state.value.busy }
            rule.onNodeWithText("Student progress").assertExists()
            rule.onNodeWithText("Last 7 days: 1 active chapters · 0 mastered").assertExists()
            rule.onNodeWithText("This week: 1 active · 0 mastered").performScrollTo().assertIsDisplayed()
            tap("Back to shared reports")
            waitUntilIdle()
            tap("Remove link 1")
            rule.onNodeWithText("Remove access", substring = false).performClick()
            rule.waitUntil(30_000) { model.state.value.progressLinks.isEmpty() && !model.state.value.busy }
        } finally {
            deleteRegressionAccount(model)
            rule.runOnIdle { model.authenticate(student, password, false, server) }
            waitUntilIdle()
            deleteRegressionAccount(model)
        }
    }

    @Test fun loginScreenAdaptsToSystemDarkMode() {
        assumeTrue(android.os.Build.VERSION.SDK_INT >= 31)
        val manager = rule.activity.getSystemService(android.app.UiModeManager::class.java)
        try {
            rule.runOnIdle { manager.setApplicationNightMode(android.app.UiModeManager.MODE_NIGHT_YES) }
            rule.waitUntil(30_000) {
                rule.activity.resources.configuration.uiMode and android.content.res.Configuration.UI_MODE_NIGHT_MASK ==
                    android.content.res.Configuration.UI_MODE_NIGHT_YES
            }
            rule.onNodeWithText("Email or username").assertExists()
            rule.activityRule.scenario.onActivity { activity ->
                assertFalse(androidx.core.view.WindowCompat.getInsetsController(
                    activity.window, activity.window.decorView).isAppearanceLightStatusBars)
            }
            rule.runOnIdle { manager.setApplicationNightMode(android.app.UiModeManager.MODE_NIGHT_NO) }
            rule.waitUntil(30_000) {
                rule.activity.resources.configuration.uiMode and android.content.res.Configuration.UI_MODE_NIGHT_MASK ==
                    android.content.res.Configuration.UI_MODE_NIGHT_NO
            }
            rule.onNodeWithText("Email or username").assertExists()
            rule.activityRule.scenario.onActivity { activity ->
                assertTrue(androidx.core.view.WindowCompat.getInsetsController(
                    activity.window, activity.window.decorView).isAppearanceLightStatusBars)
            }
        } finally {
            rule.runOnIdle { manager.setApplicationNightMode(android.app.UiModeManager.MODE_NIGHT_AUTO) }
        }
    }

    @Test fun gradeSixSubjectPathsUnlockTheirSecondChapter() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        val restartPhase = InstrumentationRegistry.getArguments().getString("curriculumRestartPhase")
        if (restartPhase == "resume") {
            try {
                assertTrue("The disposable session should survive the process stop", model.state.value.signedIn)
                rule.onNodeWithText("Explore grade lessons").performScrollTo().performClick()
                rule.waitUntil(30_000) { model.state.value.screen == "curriculum" && !model.state.value.busy }
                rule.onNodeWithText("Resume lesson: The water cycle").performScrollTo().performClick()
                rule.waitUntil(30_000) {
                    !model.state.value.busy && model.state.value.curriculumLesson?.optString("phase") == "coach"
                }
                rule.onNodeWithText("Next diagnostic question").performScrollTo().performClick()
                rule.waitUntil(30_000) {
                    !model.state.value.busy && model.state.value.curriculumLesson?.optInt("diagnostic_index") == 1
                }
                rule.onNodeWithText("Diagnostic question 2 of 2").assertExists()
            } finally {
                deleteRegressionAccount(model)
            }
            return
        }
        check(!model.state.value.signedIn) { "Run this test on a signed-out disposable installation." }
        signInForRegression(model, "subjectpaths")
        var keepAccount = false

        fun tap(label: String) = rule.onNodeWithText(label, substring = false).performScrollTo().performClick()
        fun phase(expected: String) = rule.waitUntil(30_000) {
            !model.state.value.busy && model.state.value.curriculumLesson?.optString("phase") == expected
        }
        fun verifyPath(
            subject: String,
            first: String,
            second: String,
            diagnosticAnswers: List<String>,
            practiceAnswer: String,
            explanation: String,
            nextPrompt: String,
        ) {
            tap(subject)
            rule.onNodeWithText("$second · Locked").performScrollTo().assertIsNotEnabled()
            tap(first)
            phase("diagnostic")
            for (answer in diagnosticAnswers) {
                tap(answer)
                rule.waitUntil(30_000) { !model.state.value.busy }
            }
            phase("practice")
            rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement(practiceAnswer)
            tap("Check answer")
            phase("rewrite")
            rule.onNodeWithText("Explain in your own words").performScrollTo().performTextReplacement(explanation)
            tap("Check explanation")
            phase("mastered")
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            val chapterCount = if (subject == "Science") 3 else 2
            rule.onNodeWithText("1 of $chapterCount chapters mastered").assertExists()
            tap(second)
            phase("diagnostic")
            rule.onNodeWithText(nextPrompt).assertExists()
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            tap("Back to subjects")
        }

        try {
            tap("Explore grade lessons")
            rule.waitUntil(30_000) { model.state.value.screen == "curriculum" && !model.state.value.busy }
            val firstGrade = rule.onNodeWithText("Grade 1").performScrollTo().fetchSemanticsNode().boundsInRoot
            val secondGrade = rule.onNodeWithText("Grade 2").fetchSemanticsNode().boundsInRoot
            val config = rule.activity.resources.configuration
            if (config.screenWidthDp in 376..480 && config.fontScale == 1f) {
                assertEquals(firstGrade.top, secondGrade.top, 1f)
                assertTrue(firstGrade.left < secondGrade.left)
            } else if (config.screenWidthDp in 376..480 && config.fontScale >= 2f) {
                assertEquals(firstGrade.left, secondGrade.left, 1f)
                assertTrue(firstGrade.top < secondGrade.top)
            }
            tap("Grade 6")
            verifyPath(
                "Science", "Evaporation and condensation", "The water cycle", listOf("Evaporation", "It condenses"), "condensation",
                "Evaporation turns liquid into vapor. Condensation reverses it.",
                "What is it called when water falls from clouds as rain or snow?",
            )
            tap("Continue: The water cycle · Science")
            phase("diagnostic")
            tap("Evaporation")
            phase("coach")
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            tap("Back to subjects")
            rule.onNodeWithText("Home", substring = false).performClick()
            tap("Explore grade lessons")
            rule.waitUntil(30_000) { model.state.value.screen == "curriculum" && !model.state.value.busy }
            tap("Resume lesson: The water cycle")
            phase("coach")
            if (restartPhase == "prepare") {
                keepAccount = true
                return
            }
            rule.activityRule.scenario.recreate()
            phase("coach")
            rule.onNodeWithText("Next diagnostic question").assertExists()
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            tap("Back to subjects")
            tap("Review: The water cycle · Science")
            phase("coach")
            rule.onNodeWithText("Worked example").assertExists()
            tap("Show example steps")
            rule.onNodeWithText("Step 1 of 3").assertExists()
            tap("Next example step")
            rule.onNodeWithText("As moist air cools, some vapor condenses into tiny liquid droplets that can form a cloud.")
                .assertExists()
            tap("Previous example step")
            rule.onNodeWithText("Step 1 of 3").assertExists()
            tap("Hide example steps")
            tap("Next diagnostic question")
            phase("diagnostic")
            rule.onNodeWithText("Diagnostic question 2 of 2").assertExists()
            tap("Water vapor condensing")
            phase("practice")
            rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement("evaporation")
            tap("Check answer")
            phase("coach")
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            rule.onNodeWithText("The water cycle · Repeated difficulty").assertExists()
            rule.onNodeWithText("Runoff and infiltration · Locked").performScrollTo().assertIsNotEnabled()
            tap("The water cycle · Repeated difficulty")
            phase("coach")
            tap("Try a practice question")
            phase("practice")
            rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement("precipitation")
            tap("Check answer")
            phase("rewrite")
            rule.onNodeWithText("Explain in your own words").performScrollTo()
                .performTextReplacement("Lake water evaporates, condenses into clouds, and falls as rain.")
            tap("Check explanation")
            phase("mastered")
            tap("Continue to Runoff and infiltration")
            phase("diagnostic")
            tap("Runoff")
            rule.waitUntil(30_000) {
                !model.state.value.busy && model.state.value.curriculumLesson?.optInt("diagnostic_index") == 1
            }
            tap("Loose garden soil")
            phase("practice")
            rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement("infiltration")
            tap("Check answer")
            phase("rewrite")
            rule.onNodeWithText("Explain in your own words").performScrollTo()
                .performTextReplacement("Runoff flows over the surface while infiltration moves water into soil.")
            tap("Check explanation")
            phase("mastered")
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            rule.onNodeWithText("3 of 3 chapters mastered").assertExists()
            tap("Back to subjects")
            verifyPath(
                "English", "Complete sentences", "Combining related sentences",
                listOf("The birds sang", "It has a subject and verb and expresses a complete thought"), "glowed",
                "Birds is the subject and sang is the verb.",
                "Which word best joins these ideas? The trail was steep, ___ we reached the top.",
            )
            verifyPath(
                "Social Studies", "Primary and secondary sources", "Corroborating historical evidence",
                listOf("A sailor's diary from the voyage", "A recent book that interprets the election records"),
                "secondary", "The sailor wrote the diary during the voyage.",
                "A letter says a bridge opened in 1910. Which source would independently support that date?",
            )
            tap("Back to grades")
            val otherGrades = mapOf(
                1 to "Counting on",
                2 to "Tens and ones",
                3 to "Multiplication as equal groups",
                4 to "Perimeter of rectangles",
                5 to "Volume of rectangular boxes",
                7 to "Unit rates",
                8 to "Solving one-variable equations",
                9 to "Slope between two points",
                10 to "The Pythagorean theorem",
                11 to "Exponential growth",
                12 to "Expected value",
            )
            for ((grade, chapter) in otherGrades) {
                tap("Grade $grade")
                tap("Mathematics")
                tap(chapter)
                phase("diagnostic")
                rule.onNodeWithText("Diagnostic question 1 of 2").assertExists()
                if (grade == 12) {
                    tap("$5")
                    rule.waitUntil(30_000) {
                        !model.state.value.busy && model.state.value.curriculumLesson?.optInt("diagnostic_index") == 1
                    }
                    rule.onNodeWithText("Diagnostic question 2 of 2").assertExists()
                }
                tap("Back to chapters")
                rule.waitUntil(30_000) { !model.state.value.busy }
                tap("Back to subjects")
                tap("Back to grades")
            }
        } finally {
            if (!keepAccount) deleteRegressionAccount(model)
        }
    }

    @Test fun gradeLessonCoachesAndUnlocksTheNextChapter() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        check(!model.state.value.signedIn) { "Run this test on a signed-out disposable installation." }
        signInForRegression(model, "mastery")
        try {
            fun tap(label: String) = rule.onNodeWithText(label, substring = false).performScrollTo().performClick()
            fun phase(expected: String) = rule.waitUntil(30_000) {
                !model.state.value.busy && model.state.value.curriculumLesson?.optString("phase") == expected
            }
            tap("Explore grade lessons")
            rule.waitUntil(30_000) { model.state.value.screen == "curriculum" && !model.state.value.busy }
            tap("Grade 6")
            tap("Mathematics")
            rule.onNodeWithText("Adding decimals · Locked").performScrollTo().assertIsNotEnabled()
            tap("Adding fractions")
            phase("diagnostic")
            tap("1/2")
            phase("coach")
            rule.onNodeWithText("Worked example").assertExists()
            rule.onNodeWithText(
                "You chose 1/2. Adding one quarter to three quarters must give more than three quarters."
            ).assertExists()
            rule.onNodeWithText("Saras tutor").assertIsDisplayed()
            tap("Read explanation aloud")
            rule.waitUntil(30_000) {
                rule.onAllNodesWithText("Read explanation aloud", substring = false).fetchSemanticsNodes().isNotEmpty()
            }
            tap("Show example steps")
            rule.onNodeWithText("2/5 + 3/5 = (2 + 3)/5 = 5/5 = 1.").assertExists()
            rule.onNodeWithText("Step 1 of 3").assertExists()
            tap("Next example step")
            rule.onNodeWithText("Step 2 of 3").assertExists()
            rule.onNodeWithText("Combine the pieces: 2 fifths plus 3 fifths makes 5 fifths.").assertExists()
            tap("Next example step")
            rule.onNodeWithText("Step 3 of 3").assertExists()
            rule.onNodeWithText("Next example step").assertDoesNotExist()
            tap("Previous example step")
            rule.onNodeWithText("Step 2 of 3").assertExists()
            tap("Read current example aloud")
            rule.waitUntil(30_000) {
                rule.onAllNodesWithText("Read current example aloud", substring = false).fetchSemanticsNodes().isNotEmpty()
            }
            tap("Soccer example")
            rule.onNodeWithText("A soccer player completed 2/5", substring = true).assertExists()
            tap("Gaming example")
            rule.onNodeWithText("A quest meter fills by 2/5", substring = true).assertExists()
            rule.onNodeWithText("A soccer player completed 2/5", substring = true).assertDoesNotExist()
            tap("Clear example theme")
            rule.onNodeWithText("A quest meter fills by 2/5", substring = true).assertDoesNotExist()
            tap("Hide example steps")
            rule.onNodeWithText("2/5 + 3/5 = (2 + 3)/5 = 5/5 = 1.").assertDoesNotExist()
            tap("Next diagnostic question")
            phase("diagnostic")
            tap("One whole is divided into seven equal pieces")
            phase("practice")
            tap("Show hint")
            rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement("6/8")
            tap("Check answer")
            phase("rewrite")
            rule.onNodeWithText("Dictate response").assertExists()
            if (android.os.Build.VERSION.SDK_INT < 31 ||
                !android.speech.SpeechRecognizer.isOnDeviceRecognitionAvailable(rule.activity)) {
                tap("Dictate response")
                rule.onNodeWithText("On-device dictation is unavailable. You can type your response.").assertExists()
            }
            rule.onNodeWithText("Explain in your own words").performScrollTo()
                .performTextReplacement("I add the numerators to combine both groups.")
            tap("Check explanation")
            rule.waitUntil(30_000) {
                !model.state.value.busy && model.state.value.curriculumLesson?.optString("feedback") ==
                    "What happens to the size of each piece when you combine the two groups?"
            }
            rule.onNodeWithText("What happens to the size of each piece when you combine the two groups?")
                .performScrollTo().assertIsDisplayed()
            rule.onNodeWithText("Explain in your own words").performScrollTo()
                .performTextReplacement("Add the numerators and keep the denominator unchanged.")
            tap("Check explanation")
            phase("mastered")
            rule.onNodeWithText("Concept mastered").assertExists()
            rule.onNodeWithText("Mastery badge earned").assertExists()
            rule.onNodeWithText("Diagnostic score: 1 / 2 correct").assertExists()
            tap("Continue to Adding decimals")
            phase("diagnostic")
            assertEquals("decimals", model.state.value.curriculumLesson!!.getString("chapter_id"))
            tap("0.75")
            rule.waitUntil(30_000) {
                !model.state.value.busy && model.state.value.curriculumLesson?.optInt("diagnostic_index") == 1
            }
            tap("Four tenths")
            phase("practice")
            rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement("0.68")
            tap("Check answer")
            phase("rewrite")
            rule.onNodeWithText("Explain in your own words").performScrollTo()
                .performTextReplacement("Align the decimal points to add matching place values.")
            tap("Check explanation")
            phase("mastered")
            tap("Back to chapters")
            rule.waitUntil(30_000) { !model.state.value.busy }
            tap("Open readiness check")
            val answers = listOf("2/3", "1/2 km", "(2 + 3)/7", "0.95", "2.07 m", "48 hundredths")
            answers.forEachIndexed { index, answer ->
                rule.waitUntil(30_000) {
                    !model.state.value.busy && model.state.value.readinessCheck?.optInt("index") == index
                }
                tap(answer)
            }
            rule.waitUntil(30_000) { model.state.value.readinessCheck?.optBoolean("complete") == true }
            rule.onNodeWithText("6 / 6 correct").assertExists()
            tap("Back to chapters")
            tap("Finding percentages")
            phase("diagnostic")
            rule.onNodeWithText("Diagnostic question 1 of 3").assertExists()
            tap("15")
            rule.waitUntil(30_000) {
                !model.state.value.busy && model.state.value.curriculumLesson?.optInt("diagnostic_index") == 1
            }
            tap("0.05")
            phase("coach")
            tap("Show example steps")
            tap("Gaming example")
            rule.onNodeWithText("You earn 30% of the 50 available badges. Multiply 0.30 × 50 to get 15 badges.")
                .assertExists()
            rule.onNodeWithText("Step 1 of 3").assertExists()
            tap("Clear example theme")
            tap("Next diagnostic question")
            phase("diagnostic")
            rule.onNodeWithText("Diagnostic question 3 of 3").assertExists()

            fun completePractice(answer: String, explanation: String) {
                phase("practice")
                rule.onNodeWithText("Your answer").performScrollTo().performTextReplacement(answer)
                tap("Check answer")
                phase("rewrite")
                rule.onNodeWithText("Explain in your own words").performScrollTo().performTextReplacement(explanation)
                tap("Check explanation")
                phase("mastered")
                tap("Back to chapters")
                rule.waitUntil(30_000) { !model.state.value.busy }
            }

            fun completeDiagnostic(title: String, choices: List<String>) {
                tap(title)
                choices.forEachIndexed { index, answer ->
                    rule.waitUntil(30_000) {
                        val lesson = model.state.value.curriculumLesson
                        !model.state.value.busy && lesson?.optString("phase") == "diagnostic" &&
                            lesson.optInt("diagnostic_index") == index
                    }
                    tap(answer)
                }
            }

            tap("\$2")
            completePractice("16", "Multiply sixty by 0.25 to find twenty-five percent.")
            completeDiagnostic("Introduction to algebra", listOf("7", "12", "x + 3 = 9"))
            completePractice("9", "Subtract five from both sides and the value is seven.")
            completeDiagnostic("Area of triangles", listOf("20 cm²", "A perpendicular segment to the base line", "18 m²"))
            completePractice("30", "Multiply the base by the perpendicular height and take half.")
            rule.onNodeWithText("5 of 5 chapters mastered").assertExists()
            tap("Open full readiness check")
            val fullAnswers = listOf("7/10", "5/6", "3/5 L", "0.81", "2.98", "0.77", "18", "3/4",
                "9", "12", "15", "n + 7 = 20", "18 cm²", "6 m", "15 cm²")
            fullAnswers.forEachIndexed { index, answer ->
                rule.waitUntil(30_000) {
                    !model.state.value.busy && model.state.value.readinessCheck?.optInt("index") == index
                }
                tap(answer)
            }
            rule.waitUntil(30_000) { model.state.value.readinessCheck?.optBoolean("complete") == true }
            rule.onNodeWithText("15 / 15 correct").assertExists()
            rule.onNodeWithText("Geometry: 3 / 3").assertExists()
        } finally {
            deleteRegressionAccount(model)
        }
    }

    @Test fun googleSignInReportsUnconfiguredServerWithoutChangingSession() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        check(!model.state.value.signedIn) { "Run this test on a signed-out disposable installation." }
        val port = InstrumentationRegistry.getArguments().getString("googleDisabledPort", "18763").toInt()
        rule.onNodeWithText("Study server URL").performScrollTo().performTextReplacement(fixtureUrl(port))
        rule.onNodeWithText("Sign in with Google").performScrollTo().performClick()
        rule.waitUntil(30_000) { !model.state.value.busy && model.state.value.error != null }
        rule.onNodeWithText("Google sign-in is not configured on this server.").assertExists()
        assertFalse(model.state.value.signedIn)
        assertTrue(model.session.token.isEmpty())
        rule.onNodeWithText("Create your study account").assertExists()
    }

    @Test fun separateAccountsCanSignInAndOutWithoutSharingStudyData() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        check(!model.state.value.signedIn) { "Run this test on a signed-out disposable installation." }
        val first = "accounta" + System.currentTimeMillis() + "@example.test"
        val second = "accountb" + System.currentTimeMillis()
        val password = "disposable-account-password"

        fun enter(username: String, value: String = password) {
            for ((label, text) in listOf("Email or username" to username, "Password · 10+ characters" to value, "Study server URL" to studyServer)) {
                val field = rule.onNodeWithText(label, substring = false).performScrollTo()
                field.performTextReplacement(text)
            }
        }

        fun submit(label: String, signedIn: Boolean) {
            rule.onNodeWithText(label, substring = false).performScrollTo().performClick()
            rule.waitUntil(30_000) {
                val state = model.state.value
                !state.busy && if (signedIn) state.signedIn else state.error != null
            }
        }

        fun signOut() {
            rule.onNodeWithText("Settings", substring = false).performClick()
            rule.onNodeWithText("Sign out", substring = false).performScrollTo().performClick()
            rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
            assertNull(model.state.value.error)
            assertTrue(model.session.token.isEmpty())
            assertTrue(model.state.value.documents.isEmpty())
        }

        val createdAccounts = mutableSetOf<String>()
        try {
            enter(first)
            submit("Create your study account", true)
            createdAccounts += first
            val owner = model.session.ownerId
            val previousToken = model.session.token
            uploadRegressionSample(model, "account-private.txt")
            rule.waitUntil(30_000) { model.state.value.document != null && !model.state.value.busy }
            val document = model.state.value.document!!.getString("id")
            rule.runOnIdle { model.saveOffline() }
            rule.waitUntil(30_000) { model.state.value.offlineDocuments.isNotEmpty() && !model.state.value.busy }
            signOut()
            assertNull(runBlocking { OfflineCache(rule.activity).load(studyServer, owner, document) })
            OkHttpClient().newCall(okhttp3.Request.Builder().url("$studyServer/account")
                .header("Authorization", "Bearer $previousToken").build()).execute().use {
                assertEquals(401, it.code)
            }

            enter(second)
            submit("Create your study account", true)
            createdAccounts += second
            assertNotEquals(owner, model.session.ownerId)
            assertTrue(model.state.value.documents.isEmpty())
            val foreign = runBlocking {
                runCatching { StudyRepository(rule.activity, model.session).call("/documents/$document") }.exceptionOrNull()
            }
            assertEquals(404, (foreign as? com.studycompanion.data.ApiException)?.status)
            signOut()
            rule.activityRule.scenario.recreate()
            rule.onNodeWithText("Already have an account? Sign in").performScrollTo().performClick()
            enter(second, "incorrect-disposable-password")
            submit("Sign in", false)
            rule.onNodeWithText("Email, username or password is incorrect.").assertExists()
            assertFalse(model.state.value.signedIn)
            enter(second)
            submit("Sign in", true)
            assertTrue(model.state.value.documents.isEmpty())
            deleteRegressionAccount(model)
            createdAccounts -= second

            rule.onNodeWithText("Already have an account? Sign in").performScrollTo().performClick()
            enter(first.uppercase(java.util.Locale.ROOT))
            submit("Sign in", true)
            assertEquals(owner, model.session.ownerId)
            assertEquals(listOf(document), model.state.value.documents.map { it.getString("id") })
            deleteRegressionAccount(model)
            createdAccounts -= first
        } finally {
            // Delete only accounts created by this test, even if an assertion fails mid-flow.
            val client = OkHttpClient()
            for (username in createdAccounts) {
                val body = JSONObject().put("username", username).put("password", password)
                val type = "application/json".toMediaType()
                val payload = body.toString().toRequestBody(type)
                val token = client.newCall(okhttp3.Request.Builder().url("$studyServer/auth/login").post(payload).build())
                    .execute().use { if (it.isSuccessful) JSONObject(it.body!!.string()).getString("token") else null }
                if (token != null) client.newCall(okhttp3.Request.Builder().url("$studyServer/account")
                    .header("Authorization", "Bearer $token").delete().build()).execute().close()
            }
        }
    }

    @Test fun uploadRetryAfterRefreshFailureDoesNotPostAgain() {
        val app = rule.activity.application
        val store = ViewModelStore()
        val uploads = AtomicInteger()
        val failRefresh = AtomicBoolean()
        val client = OkHttpClient.Builder().readTimeout(120, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val request = chain.request()
                if (request.method == "GET" && request.url.encodedPath == "/documents" &&
                    failRefresh.compareAndSet(true, false)) throw IOException("Injected library refresh failure")
                chain.proceed(request).also { response ->
                    if (request.method == "POST" && request.url.encodedPath == "/documents" && response.isSuccessful &&
                        uploads.incrementAndGet() == 1) failRefresh.set(true)
                }
            }.build()
        lateinit var model: StudyViewModel
        rule.runOnIdle {
            val factory = object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    modelClass.cast(StudyViewModel(app, StudyRepository(
                        app, SessionStore(app), client)))!!
            }
            model = ViewModelProvider(store, factory)[StudyViewModel::class.java]
        }
        try {
            signInForRegression(model, "uploadretry")
            uploadRegressionSample(model, "retry-upload.txt")
            rule.waitUntil(30_000) { model.state.value.error != null && !model.state.value.busy }
            assertEquals("Injected library refresh failure", model.state.value.error)
            rule.runOnIdle { model.retry() }
            rule.waitUntil(30_000) { model.state.value.screen == "configure" && !model.state.value.busy }
            assertEquals(1, uploads.get())
            assertEquals(listOf(model.state.value.document!!.getString("id")),
                model.state.value.documents.map { it.getString("id") })
        } finally {
            deleteRegressionAccount(model)
            rule.runOnIdle { store.clear() }
        }
    }

    @Test fun openOfflineResultAndSourceDisappearAtExpiry() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        signInForRegression(model, "expiry")
        try {
            uploadRegressionSample(model, "expiry-biology.txt")
            rule.waitUntil(30_000) { model.state.value.document != null && !model.state.value.busy }
            val docId = model.state.value.document!!.getString("id")
            rule.runOnIdle { model.saveOffline() }
            rule.waitUntil(30_000) { model.state.value.offlineDocuments.isNotEmpty() && !model.state.value.busy }
            rule.runOnIdle { model.openOffline(docId) }
            rule.waitUntil(30_000) { model.state.value.offlineBundle != null && !model.state.value.busy }
            rule.runOnIdle { model.startOffline(emptySet(), "", "", 1, "multiple_choice") }
            rule.waitUntil(30_000) { model.state.value.offlineQuizId != null && !model.state.value.busy }
            val quizId = model.state.value.offlineQuizId!!
            val quiz = model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0)
            val correct = quiz.getJSONArray("questions").getJSONObject(0).getInt("answer")
            rule.runOnIdle { model.answerOffline((correct + 1) % 4) }
            rule.waitUntil(30_000) { !model.state.value.busy }
            rule.runOnIdle { model.nextOffline() }
            rule.waitUntil(30_000) { !model.state.value.busy }
            val shortBundle = JSONObject(model.state.value.offlineBundle.toString())
                .put("expires_at", (System.currentTimeMillis() + 8_000) / 1000.0)
            runBlocking {
                OfflineCache(rule.activity).save(model.session.server, model.session.ownerId, shortBundle)
            }
            rule.runOnIdle { model.openOffline(docId) }
            rule.waitUntil(30_000) { !model.state.value.busy }
            rule.runOnIdle { model.resumeOffline(quizId) }
            rule.onNodeWithText("Offline result: 0 / 1").assertExists()
            rule.onNodeWithText("Read saved source").performScrollTo().performClick()
            rule.onNodeWithText("Saved source passage").assertExists()
            rule.waitUntil(15_000) { model.state.value.offlineBundle == null }
            rule.onNodeWithText("Offline result: 0 / 1").assertDoesNotExist()
            rule.onNodeWithText("Saved source passage").assertDoesNotExist()
            rule.onNodeWithText("Open saved expiry-biology").assertDoesNotExist()
        } finally {
            deleteRegressionAccount(model)
        }
    }

    private fun signInForRegression(model: StudyViewModel, prefix: String, server: String = studyServer) {
        rule.waitUntil(30_000) { !model.state.value.busy }
        rule.runOnIdle { model.authenticate(prefix + System.currentTimeMillis(), "disposable-regression-password", true, server) }
        rule.waitUntil(30_000) { model.state.value.signedIn && !model.state.value.busy }
        assertNull(model.state.value.error)
    }

    private fun uploadRegressionSample(model: StudyViewModel, filename: String) {
        val file = File(rule.activity.cacheDir, filename).apply {
            writeText("Chapter 1 Cells\nMitochondria produce usable energy through cellular respiration inside living cells.")
        }
        rule.runOnIdle { model.upload(Uri.fromFile(file)) }
    }

    private fun deleteRegressionAccount(model: StudyViewModel) {
        rule.runOnIdle { if (model.state.value.signedIn) model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
    }

    @Test fun savedMaterialSupportsAirplaneModeQuizFeedbackAndDeletion() {
        assumeTrue("This network-toggle test is for the disposable emulator", android.os.Build.MODEL.contains("sdk"))
        val restartPhase = InstrumentationRegistry.getArguments().getString("offlineRestartPhase")
        if (restartPhase == "resume") { resumeOfflineAfterRestart(); return }
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        if (model.state.value.signedIn) {
            rule.runOnIdle { model.signOut() }
            rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
        }
        rule.runOnIdle { model.authenticate("offline" + System.currentTimeMillis(), "disposable-offline-password", true, studyServer) }
        rule.waitUntil(30_000) { model.state.value.signedIn && !model.state.value.busy }
        assertNull(model.state.value.error)
        val file = File(rule.activity.cacheDir, "offline-biology.txt").apply { writeText("""
            Chapter 1 Cells
            Mitochondria produce usable energy through cellular respiration inside living cells.
            Ribosomes assemble proteins using instructions carried by messenger molecules.
        """.trimIndent()) }
        rule.runOnIdle { model.upload(Uri.fromFile(file)) }
        rule.waitUntil(30_000) { model.state.value.document != null && !model.state.value.busy }
        val docId = model.state.value.document!!.getString("id")
        rule.onNodeWithText("Save confirmed material for offline study").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "offline" && !model.state.value.busy }
        assertNull(model.state.value.error)
        rule.onNodeWithText("Open saved offline-biology").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.offlineBundle != null && !model.state.value.busy }
        fun shell(command: String): String {
            val descriptor = InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(command)
            return android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor).use { it.readBytes().toString(Charsets.UTF_8).trim() }
        }
        try {
            shell("cmd connectivity airplane-mode enable")
            shell("svc wifi disable")
            assertEquals("1", shell("settings get global airplane_mode_on"))
            rule.onNodeWithText("Offline questions · 1–50").performScrollTo().performTextClearance()
            rule.onNodeWithText("Offline questions · 1–50").performTextInput("1")
            rule.onNodeWithText("Generate offline practice").performScrollTo().performClick()
            rule.waitUntil(30_000) { model.state.value.offlineQuizId != null && !model.state.value.busy }
            assertNull(model.state.value.error)
            val quizId = model.state.value.offlineQuizId!!
            val quiz = model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0)
            val question = quiz.getJSONArray("questions").getJSONObject(0)
            val wrong = (question.getInt("answer") + 1) % 4
            rule.onNodeWithText(question.getJSONArray("choices").getString(wrong), useUnmergedTree = true).performScrollTo().performClick()
            rule.onNodeWithText("Check offline answer").performScrollTo().performClick()
            rule.waitUntil(30_000) { model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0).getJSONArray("answers").length() == 1 && !model.state.value.busy }
            rule.onNodeWithText("Read saved source").performScrollTo().performClick()
            rule.onNodeWithText("Saved source passage").assertExists()
            rule.onNodeWithText("Close saved source").performClick()
            if (restartPhase == "prepare") return // External harness kills this process after instrumentation ends.
            rule.runOnIdle { rule.activity.requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE }
            rule.waitUntil(30_000) { rule.activity.resources.configuration.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE }
            rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
            assertEquals(quizId, model.state.value.offlineQuizId)
            rule.onNodeWithText("See offline results").performScrollTo().performClick()
            rule.waitUntil(30_000) { model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0).getInt("index") == 1 && !model.state.value.busy }
            rule.onNodeWithText("Offline result: 0 / 1").assertExists()
            rule.onNodeWithText("Retry offline mistakes").performScrollTo().performClick()
            rule.waitUntil(30_000) { model.state.value.offlineQuizId != quizId && !model.state.value.busy }
            assertEquals(2, model.state.value.offlineBundle!!.getJSONArray("local_quizzes").length())
        } finally {
            shell("cmd connectivity airplane-mode disable")
            shell("svc wifi enable")
            rule.runOnIdle { rule.activity.requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT }
        }
        val manager = rule.activity.getSystemService(android.content.Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        rule.waitUntil(60_000) { manager.getNetworkCapabilities(manager.activeNetwork)?.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET) == true }
        rule.runOnIdle { model.syncOffline() }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertNull(model.state.value.error)
        assertTrue(model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0).getBoolean("synced"))
        assertFalse(model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(1).getBoolean("synced"))
        assertEquals(1, model.state.value.progress!!.getInt("quizzes_completed"))
        rule.runOnIdle { model.syncOffline() }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals(1, model.state.value.progress!!.getInt("quizzes_completed"))
        // Simulate deletion on a different client, then reconcile this device's cache.
        kotlinx.coroutines.runBlocking {
            com.studycompanion.data.StudyRepository(rule.activity, model.session).call("/documents/$docId", "DELETE")
        }
        rule.runOnIdle { model.refresh() }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertNull(model.state.value.error)
        assertNull(model.state.value.offlineBundle)
        rule.runOnIdle { model.showOffline() }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertTrue(model.state.value.offlineDocuments.isEmpty())
        rule.runOnIdle { model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
    }

    private fun resumeOfflineAfterRestart() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertTrue(model.state.value.signedIn)
        assertNotNull("Initial online refresh must fail with connectivity disabled", model.state.value.error)
        rule.onNodeWithText("Study saved material offline").performScrollTo().performClick()
        rule.waitUntil(30_000) { !model.state.value.busy && model.state.value.offlineDocuments.isNotEmpty() }
        rule.onNodeWithText("Open saved offline-biology").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.offlineBundle != null && !model.state.value.busy }
        val saved = model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0)
        assertEquals(1, saved.getJSONArray("answers").length())
        assertEquals(0, saved.getInt("index"))
        rule.onNodeWithText("Resume offline practice · question 1").performScrollTo().performClick()
        rule.onNodeWithText("See offline results").performScrollTo().performClick()
        rule.waitUntil(30_000) { !model.state.value.busy && model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0).getInt("index") == 1 }
        rule.onNodeWithText("Offline result: 0 / 1").assertExists()
        val automation = InstrumentationRegistry.getInstrumentation().uiAutomation
        for (command in listOf("cmd connectivity airplane-mode disable", "svc wifi enable")) {
            android.os.ParcelFileDescriptor.AutoCloseInputStream(automation.executeShellCommand(command)).use { it.readBytes() }
        }
        val manager = rule.activity.getSystemService(android.content.Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        rule.waitUntil(60_000) { manager.getNetworkCapabilities(manager.activeNetwork)?.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET) == true }
        rule.runOnIdle { model.syncOffline() }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals(1, model.state.value.progress!!.getInt("quizzes_completed"))
        assertTrue(model.state.value.offlineBundle!!.getJSONArray("local_quizzes").getJSONObject(0).getBoolean("synced"))
        rule.runOnIdle { model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.busy && !model.state.value.signedIn }
    }

    @Test fun unavailableAiClearlyOffersEasyLocalPractice() {
        lateinit var model: StudyViewModel
        rule.runOnIdle { model = ViewModelProvider(rule.activity)[StudyViewModel::class.java] }
        rule.waitUntil(30_000) { !model.state.value.busy }
        if (model.state.value.signedIn) {
            rule.runOnIdle { model.signOut() }
            rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
        }
        rule.onNodeWithText("Email or username").performScrollTo().performTextInput("fallback" + System.currentTimeMillis())
        rule.onNodeWithText("Password · 10+ characters").performScrollTo().performTextInput("disposable-fallback-password")
        rule.onNodeWithText("Study server URL").performScrollTo().performTextReplacement(fixtureUrl(18764))
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
        rule.onNodeWithText("Email or username").performScrollTo().performTextInput(username)
        rule.onNodeWithText("Password · 10+ characters").performScrollTo().performTextInput("disposable-scan-password")
        rule.onNodeWithText("Study server URL").performScrollTo().performTextReplacement(studyServer)
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
        val savedOwner = model.session.ownerId
        val savedServer = model.session.server
        val savedId = model.state.value.document!!.getString("id")
        rule.runOnIdle { model.saveOffline() }
        rule.waitUntil(30_000) { !model.state.value.busy }
        assertNull(model.state.value.error)
        assertTrue(model.state.value.offlineDocuments.any { it.getString("id") == savedId })
        rule.runOnIdle { model.navigate("configure") }
        rule.onNodeWithText("Questions · 1–50").performScrollTo().performTextClearance()
        rule.onNodeWithText("Questions · 1–50").performTextInput("5")
        rule.onNodeWithText("Start practice").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "quiz" && !model.state.value.busy }
        assertNull(model.state.value.error)
        assertEquals(1, model.state.value.quiz!!.getJSONObject("question").getInt("page"))
        val quizId = model.state.value.quiz!!.getString("id")
        rule.runOnIdle { model.answer(0) }
        rule.waitUntil(30_000) { !model.state.value.busy }
        rule.onNodeWithText("Read source passage").performScrollTo().performClick()
        rule.waitUntil(30_000) { !model.state.value.busy }
        rule.onNodeWithText("View original scanned page").performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "ocr" && !model.state.value.busy }
        rule.onNodeWithText("Back to study").performScrollTo().performClick()
        assertEquals("quiz", model.state.value.screen)
        assertEquals(quizId, model.state.value.quiz!!.getString("id"))
        rule.runOnIdle { model.deleteAccount() }
        rule.waitUntil(30_000) { !model.state.value.signedIn && !model.state.value.busy }
        kotlinx.coroutines.runBlocking {
            val cache = com.studycompanion.data.OfflineCache(rule.activity)
            try { assertNull(cache.load(savedServer, savedOwner, savedId)) }
            finally { cache.close() }
        }
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
        rule.onNodeWithText("Email or username").performScrollTo().performTextReplacement(username)
        rule.onNodeWithText("Password · 10+ characters").performScrollTo().performTextReplacement("disposable-test-password")
        rule.onNodeWithText("Study server URL").performScrollTo().performTextReplacement(studyServer)
        rule.onNodeWithText("Create your study account").performScrollTo().performClick()
        rule.waitUntil(30_000) {
            val state = model.state.value
            !state.busy && (state.signedIn || state.error != null)
        }
        assertTrue("Fixture registration failed: ${model.state.value.error}", model.state.value.signedIn)
        assertNull(model.state.value.error)
        rule.onNodeWithText("Your learning library").assertExists()
        // A refused connection must leave a readable failure and a working retry action.
        rule.runOnIdle {
            model.session.server = fixtureUrl(1)
            model.refresh()
        }
        rule.waitUntil(30_000) { model.state.value.error != null && !model.state.value.busy }
        rule.onNodeWithText("Retry").assertExists()
        rule.runOnIdle { model.session.server = studyServer }
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
        rule.onNodeWithText("Dictate response").assertExists()
        rule.onNodeWithText("Read latest tutor answer aloud").performScrollTo().assertIsDisplayed()
        rule.onNodeWithText("Saras tutor").assertIsDisplayed()
        assertTrue(model.state.value.tutorTurns.first().getString("answer").contains("Mitochondria"))
        rule.onNodeWithText("Read cited source").performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.source != null && !model.state.value.busy }
        rule.onNodeWithText("Close").performClick()
        screenshot("11-document-tutor")
        rule.onNodeWithText("Back to document").performScrollTo().performClick()
        rule.onNodeWithText("Start practice").performScrollTo().performClick()
        rule.waitUntil(120_000) { model.state.value.quiz != null && !model.state.value.busy }
        assertNull(model.state.value.error)
        val startedQuiz = model.state.value.quiz!!.getString("id")
        rule.onNodeWithText("Library", substring = false).performClick()
        rule.onNodeWithText("Resume ", substring = true).performScrollTo().performClick()
        rule.waitUntil(30_000) { model.state.value.screen == "quiz" && !model.state.value.busy }
        assertEquals(startedQuiz, model.state.value.quiz!!.getString("id"))
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
