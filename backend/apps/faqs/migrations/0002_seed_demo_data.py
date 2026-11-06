# Idempotent data migration: creates a demo user and a coherent set of FAQ
# entries (SaaS billing/account support topic) with real embeddings computed
# via apps.common.ai.get_embedding (the same function used at request time),
# so the demo data is immediately usable with /api/ask/.
#
# Without OPENAI_API_KEY set, get_embedding() returns deterministic stub
# vectors (see apps/common/ai.py) - not semantically meaningful, but fully
# functional for exercising the embed -> store -> search -> answer pipeline.
#
# Safe to run repeatedly: `get_or_create` keyed on (user, question) means a
# second `migrate` does not duplicate rows.

from django.db import migrations

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"

FAQ_ENTRIES = [
    (
        "How do I upgrade my subscription plan?",
        "Go to Account Settings > Billing > Change Plan, pick the new plan, and confirm. "
        "The new rate is prorated for the rest of your current billing cycle and takes "
        "effect immediately.",
    ),
    (
        "How do I downgrade my subscription plan?",
        "Go to Account Settings > Billing > Change Plan and select a lower tier. "
        "Downgrades take effect at the start of your next billing cycle, so you keep "
        "your current plan's features until then.",
    ),
    (
        "What payment methods do you accept?",
        "We accept all major credit and debit cards (Visa, Mastercard, American Express) "
        "and PayPal. Annual plans can also be paid by bank transfer on request.",
    ),
    (
        "How do I update my billing information?",
        "Go to Account Settings > Billing > Payment Method and click Edit. Changes apply "
        "to your next invoice; in-progress charges are not affected.",
    ),
    (
        "Can I get an invoice for my subscription payment?",
        "Yes. Every payment generates a PDF invoice automatically, available under "
        "Account Settings > Billing > Invoice History, and also emailed to your billing "
        "address.",
    ),
    (
        "How do I cancel my subscription?",
        "Go to Account Settings > Billing > Cancel Subscription. Your account stays "
        "active until the end of the current billing period, after which it moves to "
        "the free tier.",
    ),
    (
        "Will I be charged after I cancel my subscription?",
        "No. Cancelling stops all future billing. You will not be charged again, and you "
        "keep access to paid features until the current period ends.",
    ),
    (
        "Do you offer refunds?",
        "We offer a full refund within 14 days of your first paid charge. Contact support "
        "with your invoice number and we'll process it within 5 business days.",
    ),
    (
        "How do I reset my account password?",
        "Click 'Forgot password' on the login page and enter your account email. You'll "
        "receive a reset link valid for 1 hour.",
    ),
    (
        "How do I change the email address on my account?",
        "Go to Account Settings > Profile > Email, enter the new address, and confirm it "
        "via the verification link we send you. Your login email updates once verified.",
    ),
    (
        "Can I add multiple users to one account?",
        "Team plans support multiple seats. Go to Account Settings > Team > Invite "
        "Member and enter their email; each seat is billed at the per-user rate for your "
        "plan.",
    ),
    (
        "How do I delete my account?",
        "Go to Account Settings > Privacy > Delete Account. This permanently removes your "
        "data after a 30-day grace period, during which you can cancel the deletion by "
        "logging back in.",
    ),
    (
        "What happens to my data if my payment fails?",
        "We retry a failed payment 3 times over 7 days and email you each time. If all "
        "retries fail, your account moves to the free tier but your data is kept, not "
        "deleted.",
    ),
    (
        "Do unused subscription credits roll over to the next month?",
        "No. Plan usage (e.g. included API calls or storage) resets at the start of each "
        "billing cycle and does not carry over, on monthly or annual plans.",
    ),
    (
        "How do I view my current plan's usage limits?",
        "Go to Account Settings > Billing > Usage to see your plan's limits alongside "
        "your usage so far in the current billing cycle, updated in real time.",
    ),
]


def seed_demo_data(apps, schema_editor):
    from django.contrib.auth.hashers import make_password

    from apps.common.ai import get_embedding

    User = apps.get_model("accounts", "User")
    FAQEntry = apps.get_model("faqs", "FAQEntry")

    user, _created = User.objects.get_or_create(
        email=DEMO_EMAIL,
        defaults={
            "password": make_password(DEMO_PASSWORD),
            "first_name": "Demo",
            "last_name": "User",
            "is_active": True,
        },
    )

    for question, answer in FAQ_ENTRIES:
        # get_or_create guards against duplicate inserts on repeat `migrate`.
        entry, created = FAQEntry.objects.get_or_create(
            user=user,
            question=question,
            defaults={"answer": answer},
        )
        if created or not entry.embedding:
            entry.embedding = get_embedding(f"{question}\n{answer}")
            entry.save(update_fields=["embedding"])


def remove_demo_data(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    FAQEntry = apps.get_model("faqs", "FAQEntry")
    FAQEntry.objects.filter(user__email=DEMO_EMAIL).delete()
    User.objects.filter(email=DEMO_EMAIL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("faqs", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_data, remove_demo_data),
    ]
