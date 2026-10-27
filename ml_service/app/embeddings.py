from io import BytesIO

import numpy as np
from PIL import Image, UnidentifiedImageError

from .settings import EMBEDDING_DIMENSIONS


class ImageValidationError(ValueError):
    pass


class ResNetEmbedder:
    def __init__(self) -> None:
        import torch
        from torchvision import models, transforms

        self._torch = torch
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._preprocess = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        self._model = torch.nn.Sequential(*list(model.children())[:-1])
        self._model.eval()
        self._model.to(self._device)

    def embed(self, image_bytes: bytes) -> np.ndarray:
        try:
            with Image.open(BytesIO(image_bytes)) as source:
                image = source.convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise ImageValidationError("Upload a valid JPG, PNG, or WEBP image.") from error

        tensor = self._preprocess(image).unsqueeze(0).to(self._device)
        with self._torch.no_grad():
            feature = self._model(tensor).flatten(1)
            feature = self._torch.nn.functional.normalize(feature, p=2, dim=1)
        embedding = feature.squeeze(0).cpu().numpy().astype(np.float32)
        if embedding.shape != (EMBEDDING_DIMENSIONS,):
            raise RuntimeError(f"Expected a {EMBEDDING_DIMENSIONS}-dimensional embedding, got {embedding.shape}.")
        return embedding
