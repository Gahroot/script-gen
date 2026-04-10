from pathlib import Path

_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent / "batch-ads-system-prompt.md"
PLAYBOOK_RULES = _PLAYBOOK_PATH.read_text(encoding="utf-8").strip()

GENERATION_PROMPT = """Generate batch ad scripts for the following business.

BUSINESS INFO:
- Business Name: {business_name}
- Target Audience: {target_audience}
- City/Service Area: {city_service_area}

PAIN POINTS & SOLUTIONS:
{pain_points_solutions}

OFFER: {offer}
RISK REVERSAL: {risk_reversal}
GUARANTEES: {guarantees}
LIMITED AVAILABILITY: {limited_availability}
DISCOUNTS: {discounts}
LEAD MAGNET: {lead_magnet}

TOP STATS / CREDIBILITY:
{top_stats}

LANDING PAGE: {landing_page_url}

GENERATE EXACTLY:
- 50 hooks (standalone pattern interrupts that work with any meat) — 40 desire hooks + 10 bold claim / curiosity hooks. Ground every hook in something tangible and specific to THIS audience.
- 3 meats (problem → solution → offer, ~30 seconds each, no CTAs inside). EACH MEAT MUST COVER A DIFFERENT PAIN POINT from the intake data. Meat one → pain point one, meat two → pain point two, meat three → pain point three. Never repeat a pain point across meats. Every meat must open with a hard-hitting rehook or credibility claim — never filler or setup.
- 2 CTAs (action-oriented, short, with urgency/social proof)

OUTPUT FORMAT — return ONLY valid JSON with this exact structure, no markdown code blocks:
{{"hooks": ["hook text 1", "hook text 2", ...], "meats": ["meat text 1", "meat text 2", "meat text 3"], "ctas": ["cta text 1", "cta text 2"]}}

Every piece of text must be in teleprompter format — spell out numbers and acronyms as spoken words.

CRITICAL: Do NOT include labels like "Hook 1:", "Hook 29:", "Meat 2:", "CTA 1:" anywhere inside the script strings — not at the start, not in the middle, not anywhere. The JSON array values must contain ONLY the words the person on camera will read. Labels are added later by the formatter. If you write "Hook 29: Your plumbing…" that is WRONG. Write "Your plumbing…" instead."""


VERIFY_HOOKS_PROMPT = """You are a quality checker for batch ad hooks. Review these {count} hooks against the rules.

BUSINESS CONTEXT:
- Business: {business_name}
- Target Audience: {target_audience}
- Top Stats: {top_stats}

HOOKS TO VERIFY:
{hooks_numbered}

CHECK EACH HOOK FOR:
1. Is it either a desire hook (paints a specific outcome THIS target audience actually craves) OR a bold claim / curiosity hook (makes them need to know)? The full batch of 50 should be roughly 40 desire + 10 bold/curiosity — flag hooks that don't fit either category.
2. Is it specific and tangible — grounded in a real moment, number, scenario, or feeling for THIS audience — not vague/abstract marketing language?
3. Does it work as a STANDALONE pattern interrupt that could pair with ANY meat? It should NOT reference specific content that only appears in one meat, AND it should not say something the meats can't follow up on.
4. Is it genuinely unique from the other hooks — not just a rewording of another hook?
5. If the business is local, does it include local references where appropriate?
6. Does it ONLY use stats/claims from the provided top stats? No hallucinated numbers, revenue figures, client counts, results, or personal anecdotes. If the intake has no credibility claim, the hook must not invent one.
7. Is it in teleprompter format — numbers AND pricing spelled out in full, no acronyms?
8. Is it free of banned corporate marketing speak (elevate, transform your, you can count on, trust the experts, state-of-the-art, world-class, etc.)?

THEN CHECK THE HOOKS AS A SET:
9. HOOK PATTERN VARIETY — do the 50 hooks use varied sentence structures (questions, statements, commands, scenarios, one-liners, specific moments)? Flag hooks as failed if MORE THAN 8 share the same opening word (e.g. "Imagine…", "What if…") or the same sentence template. When flagging, prefer flagging the later occurrences so the earliest distinct ones survive.

Return ONLY valid JSON, no markdown code blocks:
{{"passed": true/false, "failed_hook_indices": [list of 0-based indices that failed], "reasons": ["reason for each failure"]}}

If all hooks pass, return {{"passed": true, "failed_hook_indices": [], "reasons": []}}"""


VERIFY_MEATS_PROMPT = """You are a quality checker for batch ad meats (body scripts). Review these meats.

BUSINESS CONTEXT:
- Business: {business_name}
- Target Audience: {target_audience}
- Offer: {offer}
- Top Stats: {top_stats}
- Pain Points: {pain_points}

MEATS TO VERIFY:
{meats_numbered}

CHECK EACH MEAT FOR:
1. Does it follow the problem → solution → value-proposition formula?
2. Does its FIRST SENTENCE hit hard — a rehook or credibility claim that keeps people from scrolling? Flag any meat opening with filler/setup like "As a business owner...", "Here at [Company]...", "We understand that...", etc. If the intake provides no real credibility claim, the opener must be a hard rehook, NOT an invented credential or anecdote.
3. Is it tight — approximately 30 seconds when read aloud (roughly 75-90 words)?
4. Does it contain NO call to action? (CTAs are separate)
5. Does it ONLY use stats/claims from the provided top stats? Flag any fabricated numbers, revenue figures, client counts, testimonials, results, or personal anecdotes that are not in the intake data.
6. Is it in teleprompter format — numbers AND pricing spelled out in full, no acronyms?
7. Would it sound natural and conversational when read on camera?
8. Is it free of banned corporate marketing speak (elevate, transform your, you can count on, state-of-the-art, world-class, etc.)?
9. PRICING RULE — by default, meats must NOT contain pricing. The ad's job is to get the click, not close the sale. RARE EXCEPTION: if this business is a local service business where a transparent hourly or flat rate IS the compelling offer (e.g. moving, cleaning, lawn care with "one forty an hour, no hidden fees"), pricing is allowed. For software, coaching, digital products, courses, info products, and most non-local services, flag any meat that includes pricing.

THEN CHECK THE MEATS AS A SET:
10. Does EACH meat cover a DIFFERENT pain point from the provided pain points list? Meat one hits pain point one, meat two hits pain point two, meat three hits pain point three. If two meats tackle the same pain point, flag the later one(s) as failed.

Return ONLY valid JSON, no markdown code blocks:
{{"passed": true/false, "failed_meat_indices": [list of 0-based indices that failed], "reasons": ["reason for each failure"]}}

If all meats pass, return {{"passed": true, "failed_meat_indices": [], "reasons": []}}"""


COMPATIBILITY_CHECK_PROMPT = """You are checking hook-meat compatibility for batch ads. In this system, ANY hook can be paired with ANY meat. They must all be compatible.

BUSINESS CONTEXT:
- Business: {business_name}
- Top Stats: {top_stats}

HOOKS:
{hooks_numbered}

MEATS:
{meats_numbered}

CHECK FOR COMPATIBILITY ISSUES:
1. Does any hook make a specific promise or reference a specific stat that NO meat backs up? If so, that hook is incompatible.
2. Would any hook sound delusional or disconnected when paired with any of the 3 meats?
3. Does any hook reference something that contradicts what the meats say?

A hook that references a general desire or outcome is FINE even if meats don't repeat it word-for-word. Only flag hooks where the pairing would sound hallucinated, contradictory, or nonsensical.

Return ONLY valid JSON, no markdown code blocks:
{{"passed": true/false, "failed_hook_indices": [list of 0-based indices of incompatible hooks], "reasons": ["reason for each failure"]}}

If all hooks are compatible with all meats, return {{"passed": true, "failed_hook_indices": [], "reasons": []}}"""


REGENERATE_HOOKS_PROMPT = """You are regenerating specific hooks that failed quality checks. Generate REPLACEMENT hooks that fix the issues.

BUSINESS INFO:
- Business Name: {business_name}
- Target Audience: {target_audience}
- City/Service Area: {city_service_area}
- Top Stats: {top_stats}

EXISTING HOOKS THAT PASSED (for context — don't duplicate these):
{passing_hooks}

FAILED HOOKS AND REASONS:
{failed_hooks_with_reasons}

Generate {count} NEW replacement hooks. Each must:
- Be either a desire hook (painting a specific outcome THIS target audience actually craves) or a bold claim / curiosity hook — the overall batch targets 40 desire + 10 bold/curiosity out of 50
- Be specific and tangible — grounded in a real moment, number, scenario, or feeling for THIS audience, not vague abstractions
- Work as a standalone pattern interrupt that pairs with ANY meat, and never promise something the meats can't follow up on
- Be unique from all existing hooks, AND use a sentence structure that varies from the existing hooks — mix questions, statements, commands, scenarios, one-liners. Do NOT open with the same word (e.g. "Imagine…", "What if…") as a pattern already heavily used above
- Use ONLY real stats from the provided data — never fabricate revenue numbers, client counts, results, testimonials, or personal anecdotes
- Contain no banned corporate marketing speak
- Be in teleprompter format (spell out numbers AND pricing in full, no acronyms)

Return ONLY valid JSON, no markdown code blocks:
{{"hooks": ["replacement hook 1", "replacement hook 2", ...]}}"""


REGENERATE_MEATS_PROMPT = """You are regenerating specific meats that failed quality checks. Generate REPLACEMENT meats that fix the issues.

BUSINESS INFO:
- Business Name: {business_name}
- Target Audience: {target_audience}
- City/Service Area: {city_service_area}
- Offer: {offer}
- Top Stats: {top_stats}
- Pain Points & Solutions: {pain_points_solutions}

EXISTING MEATS THAT PASSED (for context — do NOT reuse the pain points these already cover):
{passing_meats}

FAILED MEATS AND REASONS:
{failed_meats_with_reasons}

Generate {count} NEW replacement meats. Each must:
- Follow problem → solution → value-proposition formula
- Open with a HARD-HITTING first sentence — rehook or credibility claim, never filler or setup like "As a business owner..." or "Here at [Company]..." If the intake has no real credibility claim, open with a hard rehook — do NOT invent credentials or anecdotes
- Cover a DIFFERENT pain point from any other meat (look at the pain points list and pick one not already used by a passing meat)
- Be ~30 seconds when read (~75-90 words)
- Contain NO call to action
- Use ONLY real stats from the provided data — never fabricate revenue numbers, client counts, results, testimonials, or personal anecdotes
- Contain no banned corporate marketing speak
- Be in teleprompter format (spell out numbers AND pricing in full, no acronyms)
- Sound conversational and natural
- NOT include pricing, UNLESS this business is a local service business where a transparent hourly or flat rate IS the compelling offer (rare exception — moving, cleaning, lawn care, etc.). For software, coaching, digital products, courses, info products, and most non-local services, do not include pricing

Return ONLY valid JSON, no markdown code blocks:
{{"meats": ["replacement meat 1", ...]}}"""
