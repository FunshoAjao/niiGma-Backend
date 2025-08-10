This project is a Niigma backend built with Django REST Framework, designed to power a mobile app. It includes JWT authentication, Google Sign-In, background task processing with Celery, subscription management, notifications, and more.

# Wellness Coach API
A backend service for a mobile wellness app that helps users track menstrual cycles, nutrition, workouts, and provides AI-powered health insights.  
Features include:
- Menstrual cycle tracking and predictions
- Daily calorie and macronutrient summaries
- Workout and meal suggestions
- AI wellness coach insights
- JWT-based authentication with Google Sign-In support

## Installation

1. Clone the repository:
```bash
git https://github.com/FunshoAjao/niiGma-Backend.git
cd Niigma-Backend-Service
```

## Create & activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

## Install dependencies:
pip install -r requirements.txt

## Create .env file:

---

### 4️⃣ **Database Setup**
```md
## Database Setup
Run migrations:
```bash
python manage.py migrate

---

### 5️⃣ **Running the Application**
```md
## Run the backend server:
python manage.py runserver

## Start Celery worker:
celery -A core worker -l info

## Start Celery Beat scheduler:
celery -A core beat -l info
```

## Example .env
SECRET_KEY=your_django_secret
DEBUG=True
DATABASE_URL=postgres://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
GOOGLE_CLIENT_ID=your_google_client_id
JWT_SECRET_KEY=your_jwt_secret


## Development Tips
Always run Celery with Beat for periodic tasks

Use python manage.py createsuperuser to create admin users

Test API endpoints using Postman/Insomnia