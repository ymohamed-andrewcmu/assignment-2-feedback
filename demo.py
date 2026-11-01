"""Fictional, hand-labeled examples; never inserted into the live database."""
from datetime import datetime, timedelta, timezone


def demo_feedback():
    examples = [
        (2, "I waited 20 minutes for a latte before class. Please speed up pickup.", "Speed"),
        (3, "Coffee was good, but the morning queue moves far too slowly.", "Speed"),
        (2, "Please add another barista during the 9 a.m. rush.", "Speed"),
        (3, "Mobile orders should not take longer than the walk-in line.", "Speed"),
        (1, "I had to leave before my order was ready after a 25-minute wait.", "Speed"),
        (2, "My cappuccino was lukewarm when I collected it.", "Product quality"),
        (3, "The muffins tasted stale this morning.", "Product quality"),
        (2, "Please stop running out of oat milk by noon.", "Product quality"),
        (2, "The tables were sticky and the bins were overflowing.", "Space & cleanliness"),
        (3, "It is too noisy to study. Could you lower the music?", "Space & cleanliness"),
        (2, "Six dollars is too much for such a small iced coffee.", "Value"),
        (2, "The cashier mixed up my order and would not help fix it.", "Service"),
        (5, "The espresso was excellent and everyone was welcoming!", "No improvement requested"),
        (5, "A lovely place to meet my study group.", "No improvement requested"),
        (4, "Thanks for a great afternoon coffee.", "No improvement requested"),
        (None, "The usual thing happened again. Please fix it.", "Manual review"),
        (2, "The drink was cold, the wait was long, and the price was too high. All three need fixing.", "Manual review"),
        (4, "", None),
    ]
    now = datetime.now(timezone.utc)
    return [dict(id=f"example-{i}", created_at=(now - timedelta(hours=i * 5)).isoformat(),
                 rating=rating, comment=comment, label=label, confidence=None,
                 reason="Illustrative hand-labeled example.", source="example",
                 model=None, prompt_version="example", original_label=label, reviewed_at=None)
            for i, (rating, comment, label) in enumerate(examples)]
