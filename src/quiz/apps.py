from django.apps import AppConfig


class QuizConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"


    def ready(self) -> None:
        import quiz.signals
        
        return super().ready()
