from django.core.management.base import BaseCommand

from apps.jewellery.indexing import index_pledge_images
from apps.jewellery.models import JewelleryImage
from apps.pledges.models import Pledge


class Command(BaseCommand):
    help = "Embed pledge record images in the ML service so identification can match them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-embed every image, including those already indexed (use after changing the model version).",
        )

    def handle(self, *args, **options):
        images = JewelleryImage.objects.exclude(pledge__status=Pledge.Status.DELETED)
        if not options["all"]:
            images = images.exclude(embedding_status=JewelleryImage.EmbeddingStatus.COMPLETED)

        indexed, failed = index_pledge_images(images.order_by("created_at", "id").iterator())
        self.stdout.write(f"Indexed {indexed} pledge image(s); {failed} failed.")
        if failed:
            self.stderr.write("Failed images are marked FAILED; check the log, then run this command again.")
