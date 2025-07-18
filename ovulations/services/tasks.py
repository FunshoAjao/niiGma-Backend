import json
from celery import shared_task
from datetime import date
from accounts.models import User
from datetime import date as dt, timedelta
from core.celery import app as celery_app
from ovulations.choices import PeriodRegularity
from ovulations.services.utils import get_next_phase, get_phase_guidance
from utils.helpers.ai_service import OpenAIClient
from ..models import CycleInsight, CycleSetup, OvulationCycle, CyclePhaseType, CycleState
from django.db.models import Q
import logging
logger = logging.getLogger(__name__)

class OvulationAIAssistant:
    def __init__(self, user: User, cycle_state: CycleState | None = None):
        self.user = user
        self.cycle_state = cycle_state
        
    def generate_cycle_insight(self):
        if CycleInsight.objects.filter(
            Q(user=self.user) &
            Q(date=self.cycle_state.date) &
            Q(phase=self.cycle_state.phase)
        ).exists():
            logger.info("Cycle insight already exists for this date and phase.")
            return
        
        user = self.user
        state = self.cycle_state
        prompt = self.build_cycle_insight_prompt()
        raw = OpenAIClient.generate_response(prompt)

        try:
            parsed = json.loads(raw)
            assert "symptom" in parsed and "fertility" in parsed
        except Exception as e:
            logger.warning(f"AI insight parsing error: {e}")
            logger.warning(f"Raw: {raw}")
            return

        # Save or update insights
        for _, payload in parsed.items():
            CycleInsight.objects.update_or_create(
                user=user,
                date=state.date,
                phase=state.phase,
                headline=payload["headline"].strip(),
                defaults={
                    "detail": payload["detail"].strip(),
                    "confidence": payload.get("confidence", "Mid"),
                }
            )


    def build_cycle_insight_prompt(self):
        state = self.cycle_state
        return f"""
        You are a compassionate women's health assistant.

        The user is currently on Day {state.day_in_cycle} of their cycle, in the **{state.phase}** phase.
        Their period lasts around **{state.average_period_length} days**, and their cycle is about **{state.average_cycle_length} days**.
        They’ve tracked this for {state.total_months_tracked} months.

        Please return *two separate insights* based on this info:
        1. A health-related observation (e.g. common symptoms like headaches, bloating)
        2. A fertility-related note (e.g. ovulation, chance of pregnancy)

        Each insight should include:
        - `headline`: 1-line summary
        - `detail`: 1-line helpful explanation or tip
        - `confidence`: High / Mid / Low

        Format your final response as a **JSON object**, like:
        {{
        "symptom": {{
            "headline": "...",
            "detail": "...",
            "confidence": "Mid"
        }},
        "fertility": {{
            "headline": "...",
            "detail": "...",
            "confidence": "High"
        }}
        }}
        """.strip()
                
    def call_insight_ai(self, prompt):
        raw = OpenAIClient.generate_response_list(prompt)
        try:
            insights = json.loads(raw)
            assert isinstance(insights, list)
            return insights
        except Exception as e:
            logger.warning(f"Insight AI error: {e}")
            return []

def predict_cycle_state(user, target_date: dt):
    try:
        setup = CycleSetup.objects.only('cycle_length', 'period_length', 'regularity').get(user=user)
    except CycleSetup.DoesNotExist:
        return None

    cycle = OvulationCycle.objects.filter(user=user).order_by("-start_date").first()
    if not cycle:
        return None

    # Predict next cycles based on average length
    while cycle.end_date < target_date:
        next_start = cycle.end_date + timedelta(days=1)
        next_end = next_start + timedelta(days=setup.cycle_length or 28) - timedelta(days=1)
        cycle = OvulationCycle(start_date=next_start, end_date=next_end, user=user)

    # Calculate predicted day and phase
    day_in_cycle = (target_date - cycle.start_date).days + 1
    menstrual_end = cycle.start_date + timedelta(days=setup.period_length or 5)
    ovulation_start = cycle.end_date - timedelta(days=(setup.period_length or 5) + 14)
    ovulation_end = ovulation_start + timedelta(days=2)

    if target_date <= menstrual_end:
        phase = CyclePhaseType.MENSTRUAL
    elif menstrual_end < target_date <= ovulation_start:
        phase = CyclePhaseType.FOLLICULAR
    elif ovulation_start < target_date <= ovulation_end:
        phase = CyclePhaseType.OVULATION
    else:
        phase = CyclePhaseType.LUTEAL

    def phase_switch_dates():
        return {
            CyclePhaseType.MENSTRUAL: menstrual_end,
            CyclePhaseType.FOLLICULAR: ovulation_start,
            CyclePhaseType.OVULATION: ovulation_end,
            CyclePhaseType.LUTEAL: cycle.end_date
        }

    switch_dates = phase_switch_dates()
    next_phase_date = switch_dates.get(phase, cycle.end_date)
    days_to_next = max(0, (next_phase_date - target_date).days)

    return {
        "day_in_cycle": day_in_cycle,
        "date": target_date.isoformat(),
        "phase": phase,
        "days_to_next_phase": days_to_next,
        "next_phase": get_next_phase(phase),
        "phase_summary": get_phase_guidance().get(str(phase).capitalize(), {}),
        "is_predicted": True,
        "cycle_stats": {
            "average_cycle_length": setup.cycle_length or 28,
            "average_period_length": setup.period_length or 5,
            "regularity": setup.regularity,
            "months_tracked": None  # Optional for predictions
        },
        "insights": []  # You may not generate insights for future predictions
    }

@shared_task(name="calculate_cycle_state")
def calculate_cycle_state(user_id, target_date: dt):
    try:
        user = User.objects.get(id=user_id)
        setup = CycleSetup.objects.only('cycle_length', 'period_length', 'regularity').get(user=user)
    except CycleSetup.DoesNotExist:
        return None

    cycle = get_or_create_cycle_for_date(user, target_date)
    if not cycle:
        logger.info(f"Cycle does not exist for this user {user.email}")
        return None 

    day_in_cycle = (target_date - cycle.start_date).days + 1

    menstrual_end = cycle.start_date + timedelta(days=setup.period_length or 5)
    ovulation_start = cycle.end_date - timedelta(days=(setup.period_length or 5) + 14)
    ovulation_end = ovulation_start + timedelta(days=2)

    if target_date <= menstrual_end:
        phase = CyclePhaseType.MENSTRUAL
    elif menstrual_end < target_date <= ovulation_start:
        phase = CyclePhaseType.FOLLICULAR
    elif ovulation_start < target_date <= ovulation_end:
        phase = CyclePhaseType.OVULATION
    else:
        phase = CyclePhaseType.LUTEAL

    switch_dates = {
        CyclePhaseType.MENSTRUAL: menstrual_end,
        CyclePhaseType.FOLLICULAR: ovulation_start,
        CyclePhaseType.OVULATION: ovulation_end,
        CyclePhaseType.LUTEAL: cycle.end_date
    }

    next_phase_date = switch_dates.get(phase, cycle.end_date)
    days_to_next = max(0, (next_phase_date - target_date).days)

    # Save or update cycle state
    state, _ = CycleState.objects.update_or_create(
        user=user,
        date=target_date,
        defaults={
            "day_in_cycle": day_in_cycle,
            "phase": phase,
            "days_to_next_phase": days_to_next,
            "average_cycle_length": setup.cycle_length or 28,
            "average_period_length": setup.period_length or 5,
            "regularity": setup.regularity
        }
    )

    OvulationAIAssistant(user, state).generate_cycle_insight()
    logger.info(f"Cycle state updated for {user.email} on {target_date.isoformat()}: {state.phase} (Day {day_in_cycle})")

from datetime import timedelta

def get_or_create_cycle_for_date(user, target_date):
    """
    Returns an existing OvulationCycle that covers `target_date`,
    or creates it on the fly based on the user's setup.
    """
    setup = CycleSetup.objects.filter(user=user).first()
    if not setup:
        return None

    # 1. Check for existing cycle
    cycle = OvulationCycle.objects.filter(
        user=user,
        start_date__lte=target_date,
        end_date__gte=target_date
    ).first()

    if cycle:
        return cycle

    # 2. No cycle found — create one dynamically
    last_cycle = OvulationCycle.objects.filter(user=user).order_by("-start_date").first()

    if last_cycle:
        next_start = last_cycle.end_date + timedelta(days=1)
    else:
        next_start = setup.first_period_date or target_date

    # Keep generating future cycles until we cover target_date
    while True:
        next_end = next_start + timedelta(days=(setup.cycle_length or 28) - 1)
        if next_start <= target_date <= next_end:
            return OvulationCycle.objects.create(
                user=user,
                start_date=next_start,
                end_date=next_end,
                cycle_length=setup.cycle_length or 28,
                period_length=setup.period_length or 5,
                is_predicted=True
            )
        next_start = next_end + timedelta(days=1)


        
from datetime import date

@shared_task
def update_all_cycle_states():
    users = User.objects.filter(is_active=True, cycle_setup_records__setup_complete=True)
    for user in users:
        try:
            calculate_cycle_state.delay(user.id, date.today())  # Use .delay() to queue the task
            logger.info(f"Queued cycle state task for {user.email}")
        except Exception as e:
            logger.error(f"Error queuing task for {user.email}: {e}")

