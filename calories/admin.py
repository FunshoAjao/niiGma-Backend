from django.contrib import admin
from .models import (
    CalorieQA,
    SuggestedMeal,
    SuggestedWorkout,
    LoggedMeal,
    LoggedWorkout,
    UserCalorieStreak
)


class SuggestedMealInline(admin.TabularInline):
    model = SuggestedMeal
    extra = 0
    fields = ("date", "meal_type", "food_item", "calories", "protein", "carbs", "fats")


class SuggestedWorkoutInline(admin.TabularInline):
    model = SuggestedWorkout
    extra = 0
    fields = ("date", "title", "intensity", "estimated_calories_burned", "duration_minutes")


@admin.register(CalorieQA)
class CalorieQAAdmin(admin.ModelAdmin):
    list_display = ("user", "goal", "activity_level", "current_weight", "goal_weight", "reminder", "goal_timeline")
    search_fields = ("user__email", "user__username", "goal")
    list_filter = ("reminder", "activity_level", "weight_unit", "allow_smart_food_suggestions")
    inlines = [SuggestedMealInline, SuggestedWorkoutInline]
    
@admin.register(UserCalorieStreak)
class UserCalorieStreakAAdmin(admin.ModelAdmin):
    list_display = ("user", "current_streak", "longest_streak", "last_streak_date")
    search_fields = ("user__email", "current_streak", "last_streak_date")
    list_filter = ("user", "current_streak", "longest_streak", "last_streak_date")


@admin.register(SuggestedMeal)
class SuggestedMealAdmin(admin.ModelAdmin):
    list_display = ("calorie_goal", "date", "meal_type", "food_item", "calories")
    search_fields = ("food_item", "meal_name", "calorie_goal__user__username")
    list_filter = ("meal_type", "date")


@admin.register(SuggestedWorkout)
class SuggestedWorkoutAdmin(admin.ModelAdmin):
    list_display = ("calorie_goal", "title", "date", "intensity", "estimated_calories_burned")
    search_fields = ("title", "description", "calorie_goal__user__username")
    list_filter = ("intensity", "date")


@admin.register(LoggedMeal)
class LoggedMealAdmin(admin.ModelAdmin):
    list_display = ("user", "meal_type", "food_item", "calories", "date", "number_of_servings_or_gram_or_slices")
    search_fields = ("user__username", "food_item")
    list_filter = ("meal_type", "measurement_unit", "date")


@admin.register(LoggedWorkout)
class LoggedWorkoutAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "date", "duration_minutes", "estimated_calories_burned", "intensity")
    search_fields = ("user__username", "title", "description")
    list_filter = ("intensity", "date")
