from datetime import date

from ovulations.choices import CyclePhaseType  

def get_phase_guidance() -> dict:
    """
    Returns guidance for the given cycle phase.
    
    Args:
        phase (str): The cycle phase (e.g., "Menstrual", "Follicular", "Ovulation", "Luteal").
    
    Returns:
        dict: A dictionary containing the title, duration, and guidance for the phase.
    """
    return phase_guidance_map

phase_guidance_map = {
        "Menstrual": {
            "title": "Menstrual Phase",
            "duration": "4 - 5 days",
            "guidance": [
                "Your period's here. You're shedding last month's lining.",
                "Hormones low, mood might dip. Go easy on yourself"
            ]
        },
        "Follicular": {
            "title": "Follicular Phase",
            "duration": "4 - 5 days",
            "guidance": [
                "Hormone levels are rising. You might feel more energetic.",
                "A good time for creativity and socializing."
            ]
        },
        "Ovulation": {
            "title": "Ovulation Phase",
            "duration": "4 - 5 days",
            "guidance": [
                "Fertility peaks. Hormones high.",
                "Mood and energy often highest now."
            ]
        },
        "Luteal": {
            "title": "Luteal Phase",
            "duration": "4 - 5 days",
            "guidance": [
                "Hormones drop. You might feel tired or moody.",
                "Focus on rest and self-care."
            ]
        }
    }

# Map phases to the logical order
PHASE_SEQUENCE = [
    CyclePhaseType.MENSTRUAL,
    CyclePhaseType.FOLLICULAR,
    CyclePhaseType.OVULATION,
    CyclePhaseType.LUTEAL,
]

def get_next_phase(current_phase):
    index = PHASE_SEQUENCE.index(current_phase)
    next_index = (index + 1) % len(PHASE_SEQUENCE)
    return PHASE_SEQUENCE[next_index]

def parse_fuzzy_date(user_input: str) -> date | None:
        import dateparser
         
        """
        Attempt to parse a fuzzy natural-language date string.

        Examples:
            "21st to 23rd" ➝ returns 22nd as midpoint
            "maybe March 25" ➝ returns March 25
        """
        if "to" in user_input:
            # Handle ranges like "21st to 23rd"
            try:
                parts = user_input.split("to")
                first = dateparser.parse(parts[0].strip())
                second = dateparser.parse(parts[1].strip())
                if first and second:
                    midpoint = first + (second - first) / 2
                    return midpoint.date()
            except Exception:
                return None
        else:
            parsed = dateparser.parse(user_input)
            return parsed.date() if parsed else None