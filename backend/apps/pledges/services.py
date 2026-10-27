import re

from django.db import transaction
from django.utils import timezone

from .models import Pledge, PledgeCodeSequence


def _highest_existing_sequence(year):
    prefix = f"GS-{year}-"
    highest = 0
    for code in Pledge.objects.filter(pledge_code__startswith=prefix).values_list("pledge_code", flat=True):
        match = re.fullmatch(rf"GS-{year}-(\d+)", code)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


@transaction.atomic
def generate_pledge_code(year=None):
    year = year or timezone.localdate().year
    highest = _highest_existing_sequence(year)
    sequence, _ = PledgeCodeSequence.objects.get_or_create(
        year=year,
        defaults={"last_sequence": highest},
    )
    sequence = PledgeCodeSequence.objects.select_for_update().get(year=year)
    sequence.last_sequence = max(sequence.last_sequence, highest) + 1
    sequence.save(update_fields=["last_sequence"])
    return f"GS-{year}-{sequence.last_sequence:04d}"