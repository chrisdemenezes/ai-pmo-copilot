def clean_transcript(transcript: str) -> str:
    """Prepare transcript content before AI analysis."""
    return transcript.strip()


def extract_context(transcript: str) -> dict:
    return {
        "length": len(transcript),
        "content": transcript
    }
