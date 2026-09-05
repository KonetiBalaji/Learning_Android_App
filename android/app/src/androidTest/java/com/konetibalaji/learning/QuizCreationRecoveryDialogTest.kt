package com.konetibalaji.learning

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.accessibility.enableAccessibilityChecks
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class QuizCreationRecoveryDialogTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun learnerMustExplicitlyChooseWhetherToDiscardTheRetryRecord() {
        var kept = false
        var discarded = false
        compose.enableAccessibilityChecks()
        compose.setContent {
            MaterialTheme {
                ErrorDialog(
                    message = "The saved quiz retry record is damaged.",
                    onDismiss = { kept = true },
                    recoveryLabel = "Discard local retry record",
                    onRecovery = { discarded = true },
                )
            }
        }

        compose.onNodeWithText("Keep retry record").assertIsDisplayed().performClick()
        assertTrue(kept)
        assertFalse(discarded)

        compose.onNodeWithText("Discard local retry record").assertIsDisplayed().performClick()
        assertTrue(discarded)
    }
}
