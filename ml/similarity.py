# similarity.py
import os
import numpy as np
from PIL import Image
import torch
from torchvision import models, transforms

# -----------------------------
# Config
# -----------------------------
EMBEDDINGS_FILE = "item_embeddings.npy"
SIMILARITY_THRESHOLD = 0.85
TOP_K = 5

# Device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -----------------------------
# Preprocessing
# -----------------------------
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# -----------------------------
# Load ResNet50 (feature extractor)
# -----------------------------
model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
model = torch.nn.Sequential(*list(model.children())[:-1])
model.eval()
model.to(device)

# -----------------------------
# Load embeddings
# -----------------------------
item_embeddings = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
print(f"Loaded embeddings for {len(item_embeddings)} items.")

# -----------------------------
# Get embedding from image
# -----------------------------
def get_embedding(image):
    if isinstance(image, str):
        img = Image.open(image).convert("RGB")
    else:
        img = image.convert("RGB")

    tensor = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        feature = model(tensor)

    return feature.squeeze().cpu().numpy()

# -----------------------------
# Cosine similarity
# -----------------------------
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# -----------------------------
# Find TOP-K similar items
# -----------------------------
def find_top_k_similar(query_image, k=TOP_K):
    query_emb = get_embedding(query_image)

    scores = []

    for item, emb in item_embeddings.items():
        sim = cosine_similarity(query_emb, emb)
        scores.append((item, float(sim)))

    # Sort highest → lowest
    scores.sort(key=lambda x: x[1], reverse=True)

    results = []

    for item, score in scores[:k]:
        category, item_id = item.split("/")

        results.append({
            "category": category,
            "item_id": item_id,
            "similarity": round(score * 100, 2)
        })

    return results


# -----------------------------
# Pledge DB Similarity Search
# -----------------------------
PLEDGE_THRESHOLD = 0.60   # 60% cosine similarity → treat as a known pledged ornament
                          # Real-world photos of the same item from different angles
                          # (hanging vs. flat, close-up vs. wide) typically score 60–70%
                          # with a generic ResNet-50 backbone.

def find_similar_pledges(query_image_path, pledge_records, k=5):
    """
    Compare a query image against all pledged ornament photos stored in the
    customer database. Each customer may have multiple photos from different angles
    (front, back, hallmark, side). For each customer, evaluates all angles and
    picks the highest matching angle score.
    Returns up to k matches ranked by similarity.

    Args:
        query_image_path: str – path to the uploaded query image
        pledge_records:   list[dict] – rows from database.get_all_customers()
        k:                int – max results to return

    Returns:
        list[dict] with keys: customer (dict), similarity (float %), matched_photo (str)
        Empty list means no pledge match found → new customer.
    """
    if not pledge_records:
        return []

    query_emb = get_embedding(query_image_path)
    scores = []

    for record in pledge_records:
        photos = record.get("photos") or []
        if not photos and record.get("ornament_photo"):
            photos = [record["ornament_photo"]]

        best_sim = -1.0
        best_photo = record.get("ornament_photo", "")

        for photo_path in photos:
            if not photo_path or not os.path.exists(photo_path):
                continue
            try:
                emb = get_embedding(photo_path)
                sim = float(cosine_similarity(query_emb, emb))
                if sim > best_sim:
                    best_sim = sim
                    best_photo = photo_path
            except Exception as e:
                print(f"[Pledge Search] Error processing {photo_path}: {e}")

        if best_sim >= 0:
            rec_copy = dict(record)
            rec_copy["best_matching_photo"] = best_photo
            scores.append((rec_copy, best_sim))

    # Sort highest → lowest
    scores.sort(key=lambda x: x[1], reverse=True)

    results = []
    for record, score in scores[:k]:
        if score >= PLEDGE_THRESHOLD:
            results.append({
                "customer": record,
                "similarity": round(score * 100, 2),
                "matched_photo": record.get("best_matching_photo")
            })

    return results


# -----------------------------
# Test
# -----------------------------
if __name__ == "__main__":
    test_image = r"G:\My Drive\GoldSafe\Dataset\Necklace\necklace_001\1.webp"

    results = find_top_k_similar(test_image)

    print("\nTop similar items:\n")
    for i, r in enumerate(results, start=1):
        print(
            f"{i}. {r['category']}/{r['item_id']} "
            f"→ similarity: {r['similarity']}%"
        )
