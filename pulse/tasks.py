import logging
from decimal import Decimal
import requests
from celery import shared_task
from django.conf import settings
from .models import NotificationLog, PriceAlert
logger = logging.getLogger(__name__)

@shared_task
def check_prices():
    active_alerts = PriceAlert.objects.filter(status=PriceAlert.Status.ACTIVE)
    routes = list(active_alerts.values_list("origin", "destination").distinct())
    queued = 0
    for origin, destination in routes:
        route = f"{origin}-{destination}"
        try:
            response = requests.get(settings.PRICE_FEED_URL, params={"route": route}, timeout=10)
            response.raise_for_status()
            current_price = Decimal(str(response.json()["price"]))
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            logger.warning("Price feed failed for %s: %s", route, exc)
            continue
        for alert in active_alerts.filter(origin=origin, destination=destination):
            if current_price <= alert.threshold_price:
                send_notification.delay(alert.id, str(current_price))
                queued += 1
    return {"routes_checked": len(routes), "notifications_queued": queued}

@shared_task
def send_notification(alert_id, triggered_price):
    alert = PriceAlert.objects.filter(id=alert_id, status=PriceAlert.Status.ACTIVE).first()
    if alert is None:
        return {"sent": False, "reason": "alert_not_active_or_missing"}
    price = Decimal(str(triggered_price))
    message = (f"Price alert triggered! {alert.origin}-{alert.destination} is now ₹{price} "
               f"- below your threshold of ₹{alert.threshold_price}")
    NotificationLog.objects.create(alert=alert, triggered_price=price, message=message)
    alert.status = PriceAlert.Status.TRIGGERED
    alert.save(update_fields=["status"])
    return {"sent": True, "alert_id": alert.id}
