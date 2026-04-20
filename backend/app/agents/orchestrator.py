"""
MedBridge Orchestrator Agent.

Uses Claude with tool_use to reason across multiple steps:
  1. Understand what the user is asking
  2. Search the right databases (US/CN)
  3. Find cross-country equivalents via ATC bridge
  4. Check drug-drug interactions
  5. Synthesize a bilingual, safety-aware response

Two entry points:
  - run_condition_search(condition, from_country, to_country)
  - run_brand_translation(brand_name, from_country, to_country, other_drugs)
"""

import os
import json
import logging
import anthropic
from sqlalchemy.orm import Session
from app.tools import TOOLS, execute_tool

log = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-5"  # use Opus for complex medical reasoning

SYSTEM_PROMPT = """You are MedBridge, an expert bilingual pharmaceutical assistant fluent in both English and Chinese medical terminology.

Your role is to help patients and travelers:
1. Find recommended medicines for a condition in the US and China
2. Translate drug brand names between countries (find equivalents)
3. Check for dangerous drug-drug interactions
4. Explain dosage differences and prescription requirements

Critical safety rules you MUST follow:
- Always flag if a drug requires a prescription (Rx) — never suggest OTC alternatives to Rx drugs without warning
- Always warn about blood thinners, insulin, cancer drugs, psychiatric medications — these CANNOT be freely substituted
- Always mention if dosages differ between countries (this can be dangerous)
- Never recommend specific dosages — tell users to consult a pharmacist or doctor
- If a drug is not available in the destination country, say so clearly
- Include both English and Chinese information in your responses

Use your tools systematically:
1. First search for the drug/condition
2. Then find equivalents using the ATC bridge
3. Then check for interactions if the user has multiple drugs
4. Finally synthesize a clear, structured response

Format your final response as structured JSON with these fields:
{
  "summary_en": "brief English summary",
  "summary_zh": "brief Chinese summary",
  "recommendations": [
    {
      "brand_name_en": "...",
      "brand_name_zh": "...",
      "generic_name": "...",
      "generic_name_zh": "...",
      "country": "US" or "CN",
      "prescription_status": "OTC" or "Rx" or "controlled",
      "strength": "...",
      "manufacturer": "...",
      "indications_en": "...",
      "indications_zh": "...",
      "warnings_en": "...",
      "warnings_zh": "...",
      "atc_code": "...",
      "equivalents": [...same structure for other country...]
    }
  ],
  "interactions": [
    {
      "drug_a": "...", "drug_b": "...",
      "severity": "contraindicated|major|moderate|minor",
      "description_en": "...",
      "description_zh": "..."
    }
  ],
  "safety_flags": ["list of important safety warnings"],
  "disclaimer": "Always consult a licensed pharmacist or physician before changing medications. / 更换药物前请务必咨询持牌药剂师或医生。"
}"""


async def run_condition_search(
    condition: str,
    from_country: str = "US",
    to_country: str = "CN",
    db: Session = None,
) -> dict:
    """Mode 1: User searches by condition → get recommendations for both countries."""

    user_message = (
        f"I need to treat: {condition}\n"
        f"Please show me recommended medicines available in {from_country} and their equivalents in {to_country}. "
        f"Include both brand names, generic names in English and Chinese, prescription status, "
        f"dosage information, and any important safety warnings."
    )

    return await _run_agent(user_message, db)


async def run_brand_translation(
    brand_name: str,
    from_country: str = "US",
    to_country: str = "CN",
    other_drugs: list[str] = None,
    db: Session = None,
) -> dict:
    """Mode 2: User has a drug in one country → find equivalent in other country."""

    other_drugs_str = ""
    if other_drugs:
        other_drugs_str = f"\nI also take: {', '.join(other_drugs)}. Please check for interactions."

    user_message = (
        f"I currently take '{brand_name}' in {from_country}. "
        f"I'm traveling to {to_country} and need to find the equivalent medicine there. "
        f"Please find the equivalent drug, compare dosages, check availability, "
        f"prescription requirements, and any safety considerations.{other_drugs_str}"
    )

    return await _run_agent(user_message, db)


async def _run_agent(user_message: str, db: Session) -> dict:
    """Core agentic loop: Claude reasons + calls tools until it has a final answer."""
    messages = [{"role": "user", "content": user_message}]

    max_iterations = 8
    for iteration in range(max_iterations):
        log.info(f"Agent iteration {iteration + 1}")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Add assistant response to message history
        messages.append({"role": "assistant", "content": response.content})

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract final JSON from text response
            return _extract_final_response(response.content)

        if response.stop_reason == "tool_use":
            # Execute all tool calls in parallel conceptually, sequentially here
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    log.info(f"Tool call: {block.name}({json.dumps(block.input, ensure_ascii=False)[:100]})")
                    result = await execute_tool(block.name, block.input, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            break

    return {"error": "Agent did not complete in expected iterations", "raw": str(messages[-1])}


def _extract_final_response(content: list) -> dict:
    """Pull the JSON response out of Claude's final text block."""
    for block in content:
        if hasattr(block, "text"):
            text = block.text.strip()
            # Try to parse JSON directly
            try:
                # Strip markdown fences if present
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                return json.loads(text)
            except json.JSONDecodeError:
                # Return as plain text if not JSON
                return {
                    "summary_en": text,
                    "summary_zh": "",
                    "recommendations": [],
                    "interactions": [],
                    "safety_flags": [],
                    "disclaimer": "Always consult a licensed pharmacist or physician before changing medications.",
                }
    return {"error": "No text response from agent"}
