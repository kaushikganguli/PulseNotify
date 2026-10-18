from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import NotificationLog, PriceAlert, UserProfile
from .tasks import send_notification
User = get_user_model()

class PriceThresholdTest(TestCase):
    def test_price_below_threshold_triggers_alert(self):
        self.assertTrue(Decimal("4200") <= Decimal("4500"))
    def test_price_above_threshold_does_not_trigger(self):
        self.assertFalse(Decimal("5000") <= Decimal("4500"))
    def test_price_equal_to_threshold_triggers_alert(self):
        self.assertTrue(Decimal("4500") <= Decimal("4500"))

class NotificationLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.alert = PriceAlert.objects.create(user=self.user, origin="DEL", destination="BOM", threshold_price=4500)
    def test_notification_log_created_with_correct_message(self):
        result = send_notification.run(self.alert.id, "4200")
        log = NotificationLog.objects.get(alert=self.alert)
        self.assertEqual(log.triggered_price, Decimal("4200"))
        self.assertEqual(log.alert, self.alert)
        self.assertIn("DEL-BOM", log.message)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, PriceAlert.Status.TRIGGERED)
        self.assertTrue(result["sent"])

class AlertScopingTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass12345")
        self.user2 = User.objects.create_user(username="user2", password="pass12345")
        PriceAlert.objects.create(user=self.user1, origin="DEL", destination="BOM", threshold_price=4500)
        self.alert2 = PriceAlert.objects.create(user=self.user2, origin="BLR", destination="HYD", threshold_price=2000)
        self.client = APIClient()
    def test_user_only_sees_own_alerts(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/alerts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["origin"], "DEL")
    def test_user_cannot_deactivate_other_users_alert(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f"/api/alerts/{self.alert2.id}/")
        self.assertEqual(response.status_code, 404)
        self.alert2.refresh_from_db()
        self.assertEqual(self.alert2.status, PriceAlert.Status.ACTIVE)

class EndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
    def test_register_creates_user_profile_with_user_role(self):
        response = self.client.post("/api/auth/register/", {"username":"alice","password":"securepass123","email":"alice@example.com","role":"admin"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username="alice").profile.role, UserProfile.Role.USER)
        self.assertIn("access", response.data)
    def test_duplicate_registration_returns_400(self):
        User.objects.create_user(username="alice", password="securepass123")
        response = self.client.post("/api/auth/register/", {"username":"alice","password":"securepass123","email":"alice@example.com"}, format="json")
        self.assertEqual(response.status_code, 400)
    def test_invalid_login_returns_401(self):
        response = self.client.post("/api/auth/login/", {"username":"unknown","password":"wrong"}, format="json")
        self.assertEqual(response.status_code, 401)
    def test_mock_price_feed_known_and_unknown_route(self):
        response = self.client.get("/api/flights/price/?route=DEL-BOM")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["price"], 3000)
        self.assertLessEqual(response.json()["price"], 7000)
        self.assertEqual(self.client.get("/api/flights/price/?route=XXX-YYY").status_code, 404)
    def test_admin_summary_forbidden_for_regular_user(self):
        user = User.objects.create_user(username="regular", password="pass12345")
        self.client.force_authenticate(user=user)
        self.assertEqual(self.client.get("/api/admin/summary/").status_code, 403)
