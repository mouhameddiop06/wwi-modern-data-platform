"""
Alertes de la plateforme :
  - échec d'un run Dagster  -> notification Slack et/ou e-mail (si configurés dans .env)
  - fraîcheur des données   -> contrôle que les tables Gold ont été rafraîchies dans les 26 h

Variables .env facultatives :
  SLACK_WEBHOOK_URL                      webhook entrant Slack
  ALERT_EMAIL_TO, SMTP_HOST, SMTP_PORT,  envoi d'e-mail (ex. smtp.gmail.com:587
  SMTP_USER, SMTP_PASSWORD               avec un mot de passe d'application)
"""
import os
import smtplib
from datetime import timedelta
from email.message import EmailMessage

import requests
from dagster import (
    AssetKey,
    DefaultSensorStatus,
    RunFailureSensorContext,
    build_last_update_freshness_checks,
    build_sensor_for_freshness_checks,
    run_failure_sensor,
)


def _notify(subject: str, body: str, log) -> None:
    sent = False
    if webhook := os.getenv("SLACK_WEBHOOK_URL"):
        requests.post(webhook, json={"text": f"*{subject}*\n{body}"}, timeout=15).raise_for_status()
        sent = True
    if (to := os.getenv("ALERT_EMAIL_TO")) and os.getenv("SMTP_HOST"):
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, os.getenv("SMTP_USER", to), to
        msg.set_content(body)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=30) as smtp:
            smtp.starttls()
            if os.getenv("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(msg)
        sent = True
    if not sent:
        log.warning("Aucun canal d'alerte configuré (SLACK_WEBHOOK_URL ou SMTP) : alerte journalisée seulement.")
    log.error(f"{subject}\n{body}")


@run_failure_sensor(
    name="wwi_run_failure_alert",
    description="Envoie une alerte (Slack / e-mail) dès qu'un run de la plateforme échoue.",
    default_status=DefaultSensorStatus.RUNNING,
)
def wwi_run_failure_alert(context: RunFailureSensorContext):
    run = context.dagster_run
    failed_steps = [e.step_key for e in context.get_step_failure_events()]
    body = (
        f"Job : {run.job_name}\n"
        f"Run : {run.run_id}\n"
        f"Étapes en échec : {', '.join(filter(None, failed_steps)) or 'inconnues'}\n"
        f"Erreur : {context.failure_event.message}\n"
        f"Détail : http://localhost:3000/runs/{run.run_id}"
    )
    _notify(f"[WWI] Échec du job {run.job_name}", body, context.log)


# Les tables Gold doivent avoir été matérialisées dans les 26 dernières heures
# (job quotidien + 2 h de marge) ; sinon le contrôle passe en échec.
GOLD_FRESHNESS_ASSETS = [
    AssetKey(["gold", t]) for t in ("fact_sales", "fact_orders", "fact_purchases", "dim_customer", "dim_product")
]

gold_freshness_checks = build_last_update_freshness_checks(
    assets=GOLD_FRESHNESS_ASSETS,
    lower_bound_delta=timedelta(hours=26),
)

gold_freshness_sensor = build_sensor_for_freshness_checks(
    freshness_checks=gold_freshness_checks,
    name="gold_freshness_sensor",
    default_status=DefaultSensorStatus.RUNNING,
)
