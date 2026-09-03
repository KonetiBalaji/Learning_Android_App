"""Isolated localhost-only Android workflow fixture, never a production server.

Uses scripted grading to verify Android score display/recovery without API
charges. Real-provider scoring is tested separately by evaluate_rewrite.py.
Run: uv run python scripts/serve_qa.py --qa-only
"""
import argparse
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa-only", action="store_true")
    parser.add_argument("--binary-fixtures", action="store_true")
    parser.add_argument("--upload-response-delay", type=int, choices=range(0, 21), default=0)
    args = parser.parse_args()
    if not args.qa_only:
        parser.error("This scripted evaluator is only for QA; supply --qa-only")
    os.environ["LEARNING_AI_MODE"] = "openai" if args.binary_fixtures else "deterministic"
    os.environ["LEARNING_RUNTIME_DIR"] = str(Path(__file__).resolve().parents[2] / "artifacts" / "qa-scripted-runtime")
    os.environ["LEARNING_JWT_SECRET"] = secrets.token_hex(32)
    import app.main as api
    from app.tutor_provider import DeterministicTutorProvider, RewriteAssessment
    import uvicorn
    if args.binary_fixtures:
        # Replace the only document-provider entry point before serving requests.
        # This mode never falls back to an external provider.
        from scripts.qa_binary_questions import generate_binary_fixture
        api.generate_document_questions = generate_binary_fixture

    class ScriptedQAProvider(DeterministicTutorProvider):
        name = "scripted-binary-qa" if args.binary_fixtures else "scripted-qa"

        def assess_rewrite(self, grade, item, response):
            base = super().assess_rewrite(grade, item, response)
            return RewriteAssessment(understood=base.understood, score=4 if base.understood else 1,
                                     feedback="Scripted QA feedback: the display and recovery contract are working.",
                                     coaching=base.coaching)

    api.tutor_provider = lambda settings, interests=(): ScriptedQAProvider()
    from scripts.qa_response_fault import install_response_fault
    install_response_fault(api.app)
    if args.upload_response_delay:
        from scripts.qa_upload_delay import install_upload_delay
        install_upload_delay(api.app, args.upload_response_delay)
    uvicorn.run(api.app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
