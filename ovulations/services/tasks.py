import json
from celery import shared_task
from datetime import date
from accounts.models import User
from datetime import date as dt, timedelta
from core.celery import app as celery_app
from ovulations.choices import PeriodRegularity
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


@celery_app.task(name="calculate_cycle_state")
def calculate_cycle_state(user_id, date: dt):
    try:
        user = User.objects.get(id=user_id)
        setup = CycleSetup.objects.only('cycle_length', 'period_length', 'regularity').get(user=user)
    except CycleSetup.DoesNotExist:
        return None  

    cycle = OvulationCycle.objects.filter(
        user=user,
        start_date__lte=date,
        end_date__gte=date
    ).first()

    if not cycle:
        return None  

    # Calculate day in cycle
    day_in_cycle = (date - cycle.start_date).days + 1  # +1 to make day 1-based

    # Determine phase (approximate based on lengths)
    menstrual_end = cycle.start_date + timedelta(days=setup.period_length or 5)
    ovulation_start = cycle.end_date - timedelta(days=setup.period_length or 5 + 14)  # approx ovulation before 14 days
    ovulation_end = ovulation_start + timedelta(days=2)

    if date <= menstrual_end:
        phase = CyclePhaseType.MENSTRUAL
    elif menstrual_end < date <= ovulation_start:
        phase = CyclePhaseType.FOLLICULAR
    elif ovulation_start < date <= ovulation_end:
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
    days_to_next = max(0, (next_phase_date - date).days)

    # Create or update CycleState
    state, _ = CycleState.objects.update_or_create(
        user=user,
        date=date,
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
    logger.info(f"Cycle state updated for {user.email} on {date.isoformat()}: {state.phase} (Day {day_in_cycle})")


@shared_task
def update_all_cycle_states():
    users = User.objects.filter(is_active=True, cycle_setup_records__setup_complete=True)
    for user in users:
        try:
            calculate_cycle_state(user.id, date.today())
            logger.info(f"Queued cycle state task for {user.email}")
        except Exception as e:
            logger.error(f"Error queuing task for {user.email}: {e}")
