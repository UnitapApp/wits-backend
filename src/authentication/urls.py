from authentication.views import AuthenticateView, GetProfileView
from rest_framework.routers import DefaultRouter



router = DefaultRouter()


router.register("info", GetProfileView)
router.register("authenticate", AuthenticateView)



urlpatterns = [

]