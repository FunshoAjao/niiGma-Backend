from datetime import date
from accounts.choices import Section
from calories.services.tasks import CalorieAIAssistant
from common.responses import CustomErrorResponse, CustomSuccessResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets

from utils.helpers.services import clean_insight
from .models import *
from .serializers import CalorieAISerializer, CalorieSerializer, LoggedMealSerializer, LoggedWorkoutSerializer, MealSource, SuggestedMealSerializer, SuggestedWorkoutSerializer
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from django.db.models import Sum, F, FloatField, Value
from django.db.models.functions import Coalesce
from drf_spectacular.types import OpenApiTypes
from django.db import transaction
import django_filters
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
import logging

logger = logging.getLogger(__name__)

class CalorieViewSet(viewsets.ModelViewSet):
    queryset = CalorieQA.objects.all().order_by('-created_at')
    serializer_class = CalorieSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['goal']
    search_fields = ['user', 'goal']
    ordering_fields = '__all__'

    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'message': '',
            'data': {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            }
        })

    def get_paginated_response_for_none_records(self, data):
        return Response({
            'status': 'success',
            'message': 'No record found.',
            'data': {
                'count': 0,
                'next': None,
                'previous': None,
                'results': data
            }
        })

    def create(self, request, *args, **kwargs):
        """Create or update the user's calorie object (only one entry per user)"""
        data = request.data.copy()
        data.pop('user', None) 
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)

        validated_data = serializer.validated_data
        obj, created = CalorieQA.objects.update_or_create(
            user=request.user,
            defaults=validated_data
        )
        user = User.objects.get(id=request.user.id)
        user.is_calories_setup = True
        user.save()
        response_serializer = self.get_serializer(obj)
        message = "Calorie created successfully" if created else "Calorie updated successfully"
        return CustomSuccessResponse(data=response_serializer.data, message=message, status=201 if created else 200)


    def list(self, request, *args, **kwargs):
        """Get calories created"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response_for_none_records(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Get a single object"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomSuccessResponse(data=serializer.data)

    def update(self, request, *args, **kwargs):
        """update an instance"""
        partial = kwargs.pop('partial', False)
        
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return CustomErrorResponse(message=serializer.errors, status=400)
        
        instance.save()
        
        return CustomSuccessResponse(data=serializer.data, message="User updated successfully")

    def destroy(self, request, *args, **kwargs):
        """Delete instance"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return CustomSuccessResponse(message="Calorie deleted successfully")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @action(
        methods=["post"],
        detail=False,
        url_path="ai_prompt",
        permission_classes=[IsAuthenticated],
        serializer_class = CalorieAISerializer
    )
    def ai_prompt(self, request, *args, **kwargs):
        logger.info("Ai about to be triggered")
        user = request.user
        serializer = CalorieAISerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation error occurred: {serializer.errors}")
            return CustomErrorResponse(message=serializer.errors, status=400)

        validated_data = serializer.validated_data
        user_prompt = validated_data.get("prompt")

        ai_response = CalorieAIAssistant(user).handle_calorie_ai_interaction(Section.CALORIES, user_prompt)
        logger.info('Prompt and response generated for calorie successfully!')

        return CustomSuccessResponse(data=ai_response, message="Conversation loaded successfully!", status=201)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="daily_meal_plan/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated],
        serializer_class = CalorieAISerializer
    )
    def daily_meal_plan(self, request, day, *args, **kwargs):
        user = request.user
        day = day or timezone.now().date()
        try: 
            goal = CalorieQA.objects.get(user=user)
        except CalorieQA.DoesNotExist:
            return CustomErrorResponse(message="Calorie onboarding not done yet!", status=404)

        meals = SuggestedMeal.objects.filter(calorie_goal=goal, date=day)
        data = {
            "date": str(day),
            "daily_target": goal.daily_calorie_target,
            "meals": [
                {"meal_type": m.meal_type, "food_item": m.food_item, "calories": m.calories, 
                 "protein": m.protein, "carbs": m.carbs, "fats": m.fats}
                for m in meals
            ]
        }

        return CustomSuccessResponse(data=data, status=200)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="suggested_meal_plan_for_the_day/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated],
        serializer_class = CalorieAISerializer
    )
    def suggested_meal_plan_for_the_day(self, request, day, *args, **kwargs):
        user = request.user
        calorie = CalorieQA.objects.filter(user=user).last()

        if not calorie:
            return CustomErrorResponse(message="Calorie onboarding not done yet!", status=404)

        suggested_meals = SuggestedMeal.objects.filter(calorie_goal=calorie, date__date=day)

        if not suggested_meals.exists():
            CalorieAIAssistant(user).generate_suggested_meals_for_the_day(calorie.id, day)
            suggested_meals = SuggestedMeal.objects.filter(calorie_goal=calorie, date=day)

        serializer = SuggestedMealSerializer(suggested_meals, many=True)
        return CustomSuccessResponse(data=serializer.data, status=200)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="suggested_work_out_for_the_day/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated],
        serializer_class = CalorieAISerializer
    )
    def suggested_work_out_for_the_day(self, request, day, *args, **kwargs):
        user = request.user
        calorie = CalorieQA.objects.filter(user=user).last()

        if not calorie:
            return CustomErrorResponse(message="Calorie onboarding not done yet!", status=404)

        suggested_work_out = SuggestedWorkout.objects.filter(calorie_goal=calorie, date__date=day)

        if not suggested_work_out.exists():
            CalorieAIAssistant(user).generate_suggested_workout_with_ai(calorie.daily_calorie_target, day)
            suggested_work_out = SuggestedWorkout.objects.filter(calorie_goal=calorie, date=day)

        serializer = SuggestedWorkoutSerializer(suggested_work_out, many=True)
        return CustomSuccessResponse(data=serializer.data, status=200)

    @action(
        methods=["post"],
        detail=False,
        url_path="log_meal",
        permission_classes=[IsAuthenticated],
        serializer_class = LoggedMealSerializer
    )
    def log_meal(self, request, *args, **kwargs):
        with transaction.atomic():
            user = request.user
            serializer = LoggedMealSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomErrorResponse(message=serializer.errors, status=400)
            
            if not hasattr(self.request.user, "calorie_qa"):
                return CustomErrorResponse(message="You are yet to set up your calories profile!", status=400)
            
            validated_data = serializer.validated_data
            food_item = validated_data.get("food_item")
            barcode = validated_data.get("barcode")
            
            nutrition = CalorieAIAssistant(user, validated_data).extract_food_items_from_meal_source(
                validated_data.get("meal_source"), validated_data['number_of_servings_or_gram_or_slices'], 
                validated_data['measurement_unit'], food_item, barcode)
            
            if not nutrition:
                return CustomErrorResponse(message="Nutrition estimation failed", status=400)
            
            if validated_data['meal_source'] == MealSource.Barcode:
                food_item = nutrition.pop('food_name', None)
                validated_data['food_item'] = food_item
            else:
                nutrition.pop("food_item", None)
                
            LoggedMeal.objects.update_or_create(
                user=user,
                meal_type=validated_data['meal_type'],
                date=validated_data.get("date", timezone.now().date()),
                defaults={
                    'food_item': validated_data['food_item'],
                    'number_of_servings_or_gram_or_slices': validated_data['number_of_servings_or_gram_or_slices'],
                    'measurement_unit': validated_data['measurement_unit'],
                    **nutrition
                }
            )

            return CustomSuccessResponse(message="Meal logged successfully!", status=200)
        
    @action(
        methods=["post"],
        detail=False,
        url_path="simulate_log_meal",
        permission_classes=[IsAuthenticated],
        serializer_class = LoggedMealSerializer
    )
    def simulate_log_meal(self, request, *args, **kwargs):
        with transaction.atomic():
            user = request.user
            serializer = LoggedMealSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomErrorResponse(message=serializer.errors, status=400)
            
            if not hasattr(self.request.user, "calorie_qa"):
                return CustomErrorResponse(message="You are yet to set up your calories profile!", status=400)
            
            validated_data = serializer.validated_data
            food_item = validated_data.get("food_item")
            nutrition = CalorieAIAssistant(user).extract_food_items_from_meal_source(validated_data.get("meal_source"), food_item)
            
            if not nutrition:
                return CustomErrorResponse(message="Nutrition estimation failed", status=400)

            return CustomSuccessResponse(message="Meal logged successfully!", data=nutrition, status=200)
    
    @action(
        methods=["post"],
        detail=False,
        url_path="log_work_out",
        permission_classes=[IsAuthenticated],
        serializer_class = LoggedWorkoutSerializer
    )
    def log_work_out(self, request, *args, **kwargs):
        with transaction.atomic():
            user = request.user
            serializer = LoggedWorkoutSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomErrorResponse(message=serializer.errors, status=400)
            
            if not hasattr(self.request.user, "calorie_qa"):
                return CustomErrorResponse(message="You are yet to set up your calories profile!", status=400)
            
            validated_data = serializer.validated_data
            worked_out_calories = CalorieAIAssistant(user).estimate_logged_workout_calories(validated_data['title'], validated_data['duration_minutes'], 
                                                                   validated_data['description'], validated_data['intensity'], validated_data['steps'])
            
            if not worked_out_calories:
                return CustomErrorResponse(message="Workout estimation failed", status=400)
            LoggedWorkout.objects.update_or_create(
                user=user,
                duration_minutes =validated_data['duration_minutes'],
                estimated_calories_burned=worked_out_calories,
                title=validated_data['title'],
                date=validated_data.get("date", timezone.now().date()),
                defaults={
                    **validated_data,
                }
            )

            return CustomSuccessResponse(message="Workout logged successfully!", status=200)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="get_logged_work_out/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def get_logged_work_out(self, request, day, *args, **kwargs):
        user = request.user
        if not hasattr(self.request.user, "calorie_qa"):
                return CustomErrorResponse(message="You are yet to set up your calories profile!", status=400)
        day = date.fromisoformat(day) or timezone.now().date()
        meals = LoggedWorkout.objects.filter(user=user, date=day)
        serializer = LoggedWorkoutSerializer(meals, many=True)
        return CustomSuccessResponse(data=serializer.data, status=200)
    
    @action(
        methods=["delete"],
        detail=False,
        url_path="delete_meal/(?P<id>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def delete_meal(self, request, *args, **kwargs):
        user = request.user
        logged_meal = kwargs['id']
        try:
            meal = LoggedMeal.objects.get(user=user, id=logged_meal)
        except LoggedMeal.DoesNotExist:
            return CustomErrorResponse(message="Resource not found!")
        meal.delete()
        return CustomSuccessResponse(message="Meal deleted successfully", status=200)
    
    @action(
        methods=["delete"],
        detail=False,
        url_path="delete_work_out/(?P<id>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def delete_work_out(self, request, *args, **kwargs):
        user = request.user
        logged_meal = kwargs['id']
        try:
            meal = LoggedWorkout.objects.get(user=user, id=logged_meal)
        except LoggedWorkout.DoesNotExist:
            return CustomErrorResponse(message="Resource not found!")
        meal.delete()
        return CustomSuccessResponse(message="Workout deleted successfully", status=200)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="get_logged_meal/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def get_logged_meal(self, request, day, *args, **kwargs):
        user = request.user
        day = date.fromisoformat(day) or timezone.now().date()
        meals = LoggedMeal.objects.filter(user=user, date__date=day)
        serializer = LoggedMealSerializer(meals, many=True)
        return CustomSuccessResponse(data=serializer.data, status=200)
    
    
    @action(
        methods=["get"],
        detail=False,
        url_path="get_all_my_logged_meal",
        permission_classes=[IsAuthenticated],
        filterset_fields = ['created_at', 'date', 'meal_type', 'food_item', 'calories', 'protein', 'carbs', 'fats'],
        filter_backends = [django_filters.rest_framework.DjangoFilterBackend, SearchFilter, OrderingFilter],
        search_fields = ['date', 'user__id', 'meal_type', 'food_item', 'calories', 'protein', 'carbs', 'fats'],
        ordering_fields = '__all__'
    )
    def get_all_my_logged_meal(self, request, *args, **kwargs):
        user = request.user
        meals = LoggedMeal.objects.filter(user=user).order_by('-created_at')
        filtered_queryset = self.filter_queryset(meals)
        page = self.paginate_queryset(filtered_queryset)
        if page is None:
            return self.get_paginated_response_for_none_records([])
        serializer = LoggedMealSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(
        methods=["get"],
        detail=False,
        url_path="get_all_my_suggested_meal",
        permission_classes=[IsAuthenticated],
        filterset_fields = ['created_at', 'date', 'meal_type', 'meal_name', 'food_item', 'calories', 'protein', 'carbs', 'fats'],
        filter_backends = [django_filters.rest_framework.DjangoFilterBackend, SearchFilter, OrderingFilter],
        search_fields = ['date', 'calorie_goal__user__email', 'meal_type', 'meal_name', 'food_item', 'calories', 'protein', 'carbs', 'fats'],
        ordering_fields = '__all__'
    )
    def get_all_my_suggested_meal(self, request, *args, **kwargs):
        user = request.user
        queryset = SuggestedMeal.objects.filter(calorie_goal__user=user).order_by('-created_at')
        filtered_queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(filtered_queryset)
        if page is None:
            return self.get_paginated_response_for_none_records([])
        serializer = SuggestedMealSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["post"],
        detail=False,
        url_path="daily_comparison/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated],
        serializer_class = LoggedMealSerializer
    )
    def daily_comparison(self, request, day, *args, **kwargs):
        user = request.user
        day = day or timezone.now().date()
        goal = CalorieQA.objects.filter(user=user).last()
        if not goal:
            return CustomErrorResponse(message="No goal specified", status=404)

        suggested = SuggestedMeal.objects.filter(calorie_goal=goal, date=day)
        logged = LoggedMeal.objects.filter(user=user, date=day)

        def sum_by_meal(meals):
            return {meal_type: sum(m.calories for m in meals if m.meal_type == meal_type)
                    for meal_type in ["breakfast", "lunch", "dinner"]}

        data ={
            "date": str(day),
            "target_total": goal.daily_calorie_target,
            "suggested": sum_by_meal(suggested),
            "logged": sum_by_meal(logged),
        }

        return CustomSuccessResponse(data=data, status=200)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="compare_logged_vs_suggested/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def compare_logged_vs_suggested(self, request, day, *args, **kwargs):
        user = request.user
        day = day or timezone.now().date()
        data = CalorieAIAssistant(user=user).compare_logged_vs_suggested(day)
        return CustomSuccessResponse(data=data, status=200)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="get_nutrition_pie_chart/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def get_nutrition_pie_chart(self, request, day, *args, **kwargs):
        user = request.user
        today = day or timezone.now().date()
        
        meals = LoggedMeal.objects.filter(user=user, date=today)

        total_calories = meals.aggregate(total=Coalesce(Sum('calories'), Value(0)))['total']
    
        try:
            calorie = CalorieQA.objects.get(user=user)
        except CalorieQA.DoesNotExist:
            return CustomErrorResponse(message="Calorie onboarding not done yet!", status=404)
        calorie_goal = calorie.daily_calorie_target

        # Calories by meal type
        meal_breakdown = meals.values('meal_type').annotate(
            total_kcal=Sum('calories')
        )
        by_meal = [
            {
                "label": m['meal_type'].capitalize(),
                "percentage": round((m['total_kcal'] / calorie_goal) * 100, 1) if calorie_goal else 0,
                "kcal": m['total_kcal']
            }
            for m in meal_breakdown
        ]

        # Macro-nutrients
        macros = meals.aggregate(
            protein=Coalesce(Sum('protein'), Value(0)),
            fats=Coalesce(Sum('fats'), Value(0)),
            carbs=Coalesce(Sum('carbs'), Value(0))
        )
        total_macros = macros['protein'] + macros['fats'] + macros['carbs']
        macros_percent = {
            "protein": {
                "percentage": round((macros['protein'] / total_macros) * 100, 1) if total_macros else 0,
                "grams": round(macros['protein'], 1)
            },
            "fat": {
                "percentage": round((macros['fats'] / total_macros) * 100, 1) if total_macros else 0,
                "grams": round(macros['fats'], 1)
            },
            "carbs": {
                "percentage": round((macros['carbs'] / total_macros) * 100, 1) if total_macros else 0,
                "grams": round(macros['carbs'], 1)
            },
        }
        insight = CalorieAIAssistant(user).generate_health_insight(calorie_goal, total_calories, macros_percent, today)
        cleaned_insight = clean_insight(insight)
        
        return CustomSuccessResponse(data={
            "date": str(today),
            "calories": {
                "goal": calorie_goal,
                "consumed": total_calories,
                "left": max(0, calorie_goal - total_calories),
                "remaining":  calorie_goal - total_calories,
                "by_meal": by_meal
            },
            "macros": macros_percent,
            "health_insight": cleaned_insight
        })
        
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='day',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.PATH,
                description='Date in YYYY-MM-DD format',
                required=True
            )
        ]
    )
    @action(
        methods=["get"],
        detail=False,
        url_path="get_daily_summary/(?P<day>[^/.]+)",
        permission_classes=[IsAuthenticated]
    )
    def get_daily_summary(self, request, day, *args, **kwargs):
        user = request.user
        target_date = date.fromisoformat(day) if day else timezone.now().date()

        suggested_meals = SuggestedMeal.objects.filter(calorie_goal__user=user, date__date=target_date)
        logged_meals = LoggedMeal.objects.filter(user=user, date__date=target_date)

        suggested_workout = SuggestedWorkout.objects.filter(calorie_goal__user=user, date__date=target_date).first()
        logged_workouts = LoggedWorkout.objects.filter(user=user, date=target_date)

        total_logged_meal_calories = logged_meals.aggregate(total=Sum('calories'))['total'] or 0
        total_logged_burn = logged_workouts.aggregate(total=Sum('estimated_calories_burned'))['total'] or 0

        # Macro_nutrient totals from logged meals
        macro_agg = logged_meals.aggregate(
            protein=Sum('protein'),
            fat=Sum('fats'),
            carbs=Sum('carbs'),
        )
        total_protein = macro_agg['protein'] or 0
        total_fat = macro_agg['fat'] or 0
        total_carbs = macro_agg['carbs'] or 0

        # Macro_nutrient goals
        macros = user.calorie_qa.macro_nutrient_targets

        return CustomSuccessResponse(
            data={
                "date": target_date,
                "calorie_goal": user.calorie_qa.daily_calorie_target,
                "calories": {
                    "consumed": total_logged_meal_calories,
                    "goal": user.calorie_qa.daily_calorie_target,
                    "left": max(user.calorie_qa.daily_calorie_target - total_logged_meal_calories, 0)
                },
                "meals": {
                    "suggested": suggested_meals.aggregate(total=Sum('calories'))['total'] or 0,
                    "logged": total_logged_meal_calories,
                    "difference": total_logged_meal_calories - (user.calorie_qa.daily_calorie_target or 0)
                },
                "workout": {
                    "suggested": suggested_workout.estimated_calories_burned if suggested_workout else 0,
                    "logged": total_logged_burn,
                    "difference": total_logged_burn - (suggested_workout.estimated_calories_burned if suggested_workout else 0)
                },
                "macro_nutrients": {
                    "protein": {
                        "logged": total_protein,
                        "goal": macros["protein"]
                    },
                    "fat": {
                        "logged": total_fat,
                        "goal": macros["fat"]
                    },
                    "carbs": {
                        "logged": total_carbs,
                        "goal": macros["carbs"]
                    },
                },
                "net_calories": total_logged_meal_calories - total_logged_burn
            }
        )