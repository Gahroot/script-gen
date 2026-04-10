from app.schemas import GeneratedScripts, IntakeData


def format_markdown(scripts: GeneratedScripts, data: IntakeData) -> str:
    lines: list[str] = []

    # Header
    lines.append(f"# {data.business_name.upper()} - 300 VIDEO ADS")
    lines.append("# BATCH CONTENT TELEPROMPTER")
    lines.append("# For Video Ads (TikTok/Reels/Shorts/Meta Ads)")
    lines.append(f"# Offer: {data.offer}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Part 1: Hooks
    lines.append("# PART 1: HOOKS (50 total)")
    lines.append("")

    for i, hook in enumerate(scripts.hooks, 1):
        lines.append("")
        lines.append(f"**HOOK {i}:**")
        lines.append("")
        lines.append(f'"{hook}"')
        lines.append("")
        lines.append("")
        lines.append("---")

    lines.append("")

    # Part 2: Meats
    lines.append("# PART 2: MEATS (3 total)")
    lines.append("")

    for i, meat in enumerate(scripts.meats, 1):
        lines.append("")
        lines.append(f"## MEAT {i}")
        lines.append("")
        lines.append("```")
        lines.append(meat)
        lines.append("```")
        lines.append("")
        lines.append("")
        lines.append("---")

    lines.append("")

    # Part 3: CTAs
    lines.append("# PART 3: CTAs (2 total)")
    lines.append("")

    for i, cta in enumerate(scripts.ctas, 1):
        lines.append("")
        lines.append(f"**CTA {i}:**")
        lines.append("")
        lines.append(f'"{cta}"')
        lines.append("")
        lines.append("")
        lines.append("---")

    lines.append("")

    # Quick Reference
    lines.append("# QUICK REFERENCE")
    lines.append("")
    lines.append(f"**Offer:** {data.offer}")
    lines.append("")
    lines.append("**All hooks work with all meats** (universal positioning)")
    lines.append("")
    lines.append("**Total combinations:** 50 × 3 × 2 = 300 ads")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Filming Tips
    lines.append("# FILMING TIPS")
    lines.append("")
    lines.append("- Read hooks with energy - first 3 seconds determine if they scroll")
    lines.append("- Pause briefly between each hook/meat/CTA for easy editing")
    lines.append("- Meats should feel conversational, not scripted")
    lines.append("- CTAs should be direct - tell them exactly what to do")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Created for: {data.business_name}*")
    lines.append(f"*Offer: {data.offer}*")
    lines.append("*Ready for teleprompter*")

    return "\n".join(lines)
