# ovulation/views.py
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone
from accounts.models import User
from datetime import timedelta, datetime
from rest_framework.exceptions import NotFound
from ovulations.services.tasks import calculate_cycle_state, predict_cycle_state
from ovulations.services.utils import get_next_phase, get_phase_guidance, parse_fuzzy_date
from .models import CycleInsight, CycleSetup, CycleState, OvulationCycle, OvulationLog
from .serializers import CycleInsightSerializer, CycleOnboardingSetUpSerializer, CycleSetupSerializer, InsightBlockSerializer, OvulationLogSerializer
from common.responses import CustomSuccessResponse, CustomErrorResponse

class CycleSetupViewSet(viewsets.ModelViewSet):
    queryset = CycleSetup.objects.all()
    serializer_class = CycleSetupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user

        # Check if a setup already exists for this user
        if CycleSetup.objects.filter(user=user, setup_complete=True).exists():
            return CustomErrorResponse(message="You already have a cycle setup.")

        data = request.data.copy()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        setup_complete = all([
            data.get("first_period_date"),
            data.get("period_length"),
            data.get("cycle_length")
        ])
        serializer.save(user=user, setup_complete=setup_complete)
        user.is_ovulation_tracker_setup = True
        user.save()
        
        if data.get("first_period_date") and data.get("period_length") and data.get("cycle_length"):
               start_date_str = data.get("first_period_date")  # e.g., "2025-06-20"
               start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

               cycle_length = int(data.get("cycle_length"))
               end_date = start_date + timedelta(days=cycle_length - 1)

               OvulationCycle.objects.create(
                    user=user,
                    start_date=start_date,
                    end_date=end_date,
                    cycle_length=data.get("cycle_length"),
                    period_length=data.get("period_length"),
                    is_predicted=False
                )
               calculate_cycle_state.delay(user.id, start_date)
        return CustomSuccessResponse(data=serializer.data, message="cycle set up created successfully!")
    
    def update(self, request, *args, **kwargs):
        raise NotFound()
        
    @action(detail=False,
            methods=["post"],
            url_path="log_entry",
            serializer_class=OvulationLogSerializer
    )
    def log_entry(self, request):
        """
        Log a new ovulation entry for the user.
        """
        serializer = OvulationLogSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)

        log = serializer.save(user=request.user)
        calculate_cycle_state.delay(request.user.id, log.date)
        return CustomSuccessResponse(message="Log entry created successfully.", data=serializer.data)
    
    @action(
        detail=False,
        methods=["put"],
        url_path="update_log_entry/(?P<log_id>[^/.]+)",
        serializer_class=OvulationLogSerializer
    )
    def update_log_entry(self, request, log_id=None):
        """
        Update an existing ovulation log entry for the user.
        """
        if not log_id:
            return CustomErrorResponse(message="Log ID is required.", status=400)

        try:
            log_entry = request.user.ovulation_logs.get(id=log_id)
        except OvulationLog.DoesNotExist:
            return CustomErrorResponse(message="Log entry not found.", status=404)

        serializer = OvulationLogSerializer(log_entry, data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)

        updated_log = serializer.save()
        
        calculate_cycle_state.delay(request.user.id, updated_log.date)  # ✅ Use updated date

        return CustomSuccessResponse(message="Log entry updated successfully.", data=serializer.data)

    
    @action(detail=False,
            methods=["get"],
            url_path="get_logs")
    def get_logs(self, request):
        """
        Retrieve all ovulation logs for the authenticated user.
        """
        logs = OvulationLogSerializer(request.user.ovulation_logs.all(), many=True).data
        return CustomSuccessResponse(data=logs)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                description="date in YYYY-MM-DD format to get cycle state for that date. Defaults to today if not specified.",
                required=False,
                type=str,
            )
        ]
    )
    @action(detail=False,
            methods=["get"],
            url_path="get_logs_by_date")
    def get_logs_by_date(self, request):
        """
        Retrieve ovulation logs for a specific date (defaults to today if not specified).
        """
        date_str = request.query_params.get("date")
        try:
            selected_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        except ValueError:
            return CustomErrorResponse(message="Invalid date format. Use YYYY-MM-DD", status=400)
        
        logs = OvulationLogSerializer(
            request.user.ovulation_logs.filter(date=selected_date), many=True
        ).data
        
        return CustomSuccessResponse(data=logs)
    
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                description="date in YYYY-MM-DD format to get cycle state for that date. Defaults to today if not specified.",
                required=False,
                type=str,
            )
        ]
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="get_cycle_state"
    )
    def get_cycle_state(self, request):
        """
        Return cycle state for a given date (defaults to today if not specified).
        """
        date_str = request.query_params.get("date")
        try:
            selected_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        except ValueError:
            return CustomErrorResponse(message="Invalid date format. Use YYYY-MM-DD", status=400)
        user = request.user
        today = timezone.now().date()
        if selected_date > today:
            data = predict_cycle_state(user, selected_date)
            if not data:
                return CustomErrorResponse(message="Prediction unavailable", status=404)
            return CustomSuccessResponse(data=data)
        
        state = CycleState.objects.filter(user=user, date=selected_date).order_by("-date").first()
        if not state:
            return CustomErrorResponse(message="Cycle state not found for today.", status=404)
        insights = CycleInsight.objects.filter(user=user, date=state.date)
        data = {
            "day_in_cycle": state.day_in_cycle,
            "date": state.date.isoformat(),
            "phase": state.phase,
            "days_to_next_phase": state.days_to_next_phase,
            "next_phase": get_next_phase(state.phase), 
            "phase_summary": get_phase_guidance().get(str(state.phase).capitalize(), {}),
            "cycle_stats": {
                "average_cycle_length": state.average_cycle_length,
                "average_period_length": state.average_period_length,
                "regularity": state.regularity,
                "months_tracked": state.total_months_tracked,
            },
            "insights": CycleInsightSerializer(insights, many=True).data
        }

        return CustomSuccessResponse(data=data)
        
    @action(
        detail=False,
        methods=["get"],
        url_path="get_insights"
    )
    def get_insights(self, request):
        user = request.user
        today = timezone.now().date()

        try:
            CycleState.objects.get(user=user, date=today)
        except CycleState.DoesNotExist:
            return CustomSuccessResponse(message="Cycle state not found for today.", status=404)

        insights = CycleInsight.objects.filter(user=user, date=today)
        data = {
            "symptom_insight": None,
            "fertility_insight": None,
        }

        for insight in insights:
            if "fertility" in insight.headline.lower():
                data["fertility_insight"] = InsightBlockSerializer(insight).data
            else:
                data["symptom_insight"] = InsightBlockSerializer(insight).data

        # Fallback if missing
        if not data["symptom_insight"]:
            data["symptom_insight"] = {
                "headline": "Log your symptoms to get personalized insights.",
                "detail": "Your current cycle data helps us guide your well-being.",
                "confidence": "Low"
            }

        if not data["fertility_insight"]:
            data["fertility_insight"] = {
                "headline": "Stay consistent to improve prediction.",
                "detail": "We’ll estimate your fertile window as we get more logs.",
                "confidence": "Low"
            }

        return CustomSuccessResponse(data=data)

    @action(detail=False, methods=["get"], url_path="current")
    def current_setup(self, request):
        try:
            setup = self.get_queryset().latest("created_at")
        except CycleSetup.DoesNotExist:
            return CustomErrorResponse(message="No cycle setup found.", status=404)

        return CustomSuccessResponse(data=CycleSetupSerializer(setup).data)

    @action(detail=False, 
            methods=["post"],
            url_path="setup_or_update",
            serializer_class=CycleOnboardingSetUpSerializer,
    )
    def setup_or_update(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        
        validated_data = serializer.validated_data
        user = request.user
        
        return self.handle_cycle_setup_step(user, validated_data)


    def handle_cycle_setup_step(self, user : User, validated_data: dict):
        from django.utils.dateparse import parse_date
        from datetime import timedelta
        """
        Accepts a step in the AI setup chat and stores interim answers. When final step is reached,
        it calculates and saves the ovulation cycle.
        """
        
        step = validated_data['step']
        answer = validated_data['answer']
        
        record, _ = CycleSetup.objects.get_or_create(user=user, setup_complete=False)

        try:
            if step == "first_period_date":
                parsed_date = parse_fuzzy_date(answer)
                print(f"Parsed date: {parsed_date}")
                if not parsed_date:
                    return CustomErrorResponse(message="Could not understand the date you entered.")
                record.first_period_date = parsed_date or parse_date(answer)  # Expecting ISO format or pre-parsed
            elif step == "period_length":
                if not answer.isdigit():
                    return CustomErrorResponse(message="Please provide a numeric value.")
                record.period_length = int(answer)
            elif step == "cycle_length":
                if not answer.isdigit():
                    return CustomErrorResponse(message="Please provide a numeric value.")
                record.cycle_length = int(answer)
            elif step == "regularity":
                record.regularity = str(answer).lower() == "regular"

            record.save()
            
            if OvulationCycle.objects.filter(user=user, start_date=record.first_period_date).exists():
                return CustomErrorResponse(message="Cycle already recorded for this start date.")

            # When all info is collected, generate the OvulationCycle
            print(f"Current record: {record} {record.first_period_date}, {record.period_length}, {record.cycle_length}")
            if record.first_period_date and record.period_length and record.cycle_length:
                start_date = record.first_period_date
                end_date = start_date + timedelta(days=record.cycle_length - 1)

                OvulationCycle.objects.create(
                    user=user,
                    start_date=start_date,
                    end_date=end_date,
                    cycle_length=record.cycle_length,
                    period_length=record.period_length,
                    is_predicted=False
                )

                record.setup_complete = True
                record.save()
                return CustomSuccessResponse(message="Cycle setup complete.")

            return CustomSuccessResponse(message="Step saved. Continue to next.")

        except Exception as e:
            return CustomErrorResponse(message=str(e), status=400)
        