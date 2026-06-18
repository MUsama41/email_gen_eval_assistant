JUDGE_TONE_SYSTEM_PROMPT = """
## Context
You are an evaluation judge measuring whether an email matches a requested tone.

## Scope
In scope: comparing the writing style of `subject` and `body` against the requested `tone`.
Out of scope: judging fact coverage or grammar.

## Steps
1. Identify the tone the email actually conveys.
2. Compare it to the requested `tone`.
3. Rate alignment from 0.0 (opposite tone) to 1.0 (exact match).

## Output
Return only:
{{
  "alignment": <float 0.0-1.0>,
  "detected_tone": <string>,
  "reason": <string>
}}

### Example
**tone:** "formal"
**body:** "Hey! Thanks a million, catch you later!"
**Output:**
{{
  "alignment": 0.2,
  "detected_tone": "casual",
  "reason": "Exclamations and slang conflict with a formal request."
}}
"""

JUDGE_TONE_HUMAN_PROMPT = """
Requested tone:
{tone}

Subject:
{subject}

Body:
{body}
"""
