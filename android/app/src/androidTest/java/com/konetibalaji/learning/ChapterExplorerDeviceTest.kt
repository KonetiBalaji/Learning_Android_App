package com.konetibalaji.learning

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.runners.Parameterized

/**
 * Device-level coverage for the thirteen explorers that previously had only
 * local JVM model/routing tests. Each case renders the production composable,
 * finds its visible heading, operates a real learner control and observes the
 * resulting selected state on the emulator.
 */
@RunWith(Parameterized::class)
class ChapterExplorerDeviceTest(private val example: ExplorerExample) {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun explorerRendersAndRespondsToSelection() {
        compose.setContent {
            MaterialTheme {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    InteractiveLessonExplorer(example.subjectId, example.chapterId)
                }
            }
        }

        compose.onNodeWithText(example.heading).assertIsDisplayed()
        compose.onNodeWithText(example.action).performScrollTo().performClick()
        compose.onNodeWithText(example.selectedText).performScrollTo().assertIsDisplayed()
    }

    data class ExplorerExample(
        val subjectId: String,
        val chapterId: String,
        val heading: String,
        val action: String,
        val selectedText: String,
    ) {
        override fun toString(): String = "$subjectId/$chapterId"
    }

    companion object {
        @JvmStatic
        @Parameterized.Parameters(name = "{0}")
        fun examples() = listOf(
            ExplorerExample("math", "decimals", "Explore decimal place value", "Explore Ones", "Selected: Ones"),
            ExplorerExample("math", "percentages", "Explore percentages", "Show 50%", "Selected: 50%"),
            ExplorerExample("math", "algebra", "Balance an equation", "Subtract 3 from both sides", "Selected: Subtract 3 from both sides"),
            ExplorerExample("math", "geometry", "Explore triangle area", "Base 8, height 5", "Selected: Base 8, height 5"),
            ExplorerExample("science", "matter", "Explore particle models", "Liquid", "Selected: Liquid"),
            ExplorerExample("science", "force-and-motion", "Explore constant speed", "3 m/s for 4 s", "Selected: 3 m/s for 4 s"),
            ExplorerExample("science", "ecosystems", "Trace ecosystem energy", "Grasshopper →", "Selected: Grasshopper"),
            ExplorerExample("english", "reading-comprehension", "Build an inference", "Inference", "Selected: Inference"),
            ExplorerExample("english", "vocabulary", "Build word meaning", "Root: help", "Selected: Root: help"),
            ExplorerExample("english", "writing", "Explore paragraph structure", "Evidence", "Selected: Evidence"),
            ExplorerExample("social", "history", "Evaluate historical sources", "A photograph taken at the event", "Selected: A photograph taken at the event"),
            ExplorerExample("social", "civics", "Trace a civic decision", "2. Public input", "Selected: 2. Public input"),
            ExplorerExample("social", "economics", "Explore supply and demand", "Price 4", "Selected: Price 4"),
        )
    }
}
