from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import os
import time
from ml.similarity import find_top_k_similar, find_similar_pledges
import database

app = Flask(__name__)
app.secret_key = "goldsafe_secret_key_muthoot"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Database
database.init_db()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    image = request.files.get("image")

    if not image:
        return "No image uploaded", 400

    filename = image.filename or f"webcam_{int(time.time())}.jpg"
    image_path = os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/")
    image.save(image_path)

    # 1. Search reference dataset for similar jewellery items
    dataset_results = find_top_k_similar(image_path)

    # 2. Search pledge database for similar ornaments already registered
    pledge_records = database.get_all_customers()
    pledge_results = find_similar_pledges(image_path, pledge_records, k=5)

    return render_template(
        "results.html",
        query_image=image_path,
        results=dataset_results,
        pledge_results=pledge_results,
        is_new_customer=(len(pledge_results) == 0)
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        aadhar = request.form.get("aadhar")

        # Support multiple photos via getlist('images') or single 'image'
        uploaded_files = request.files.getlist("images")
        if not uploaded_files or not uploaded_files[0].filename:
            single = request.files.get("image")
            if single and single.filename:
                uploaded_files = [single]

        valid_images = [img for img in uploaded_files if img and img.filename]

        if not name or not phone or not aadhar or not valid_images:
            return "All fields (Name, Phone No, Aadhaar No, and at least one Ornament Photo) are required.", 400

        saved_paths = []
        base_time = int(time.time())
        phone_suffix = phone[-4:] if len(phone) >= 4 else "item"

        for idx, img in enumerate(valid_images, start=1):
            ext = os.path.splitext(img.filename)[1] or ".jpg"
            if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
                ext = ".jpg"
            filename = f"pledge_{base_time}_{phone_suffix}_angle{idx}{ext}"
            image_path = os.path.join(UPLOAD_FOLDER, filename).replace("\\", "/")
            img.save(image_path)
            saved_paths.append(image_path)

        customer = database.add_customer(name, phone, aadhar, saved_paths)
        return render_template("register_success.html", customer=customer)

    return render_template("register.html")

@app.route("/customers")
def customers():
    customer_list = database.get_all_customers()
    return render_template("customers.html", customers=customer_list)

@app.route("/delete/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    customer = database.get_customer_by_id(customer_id)
    if customer:
        photos = customer.get("photos", [])
        if not photos and customer.get("ornament_photo"):
            photos = [customer["ornament_photo"]]
        database.delete_customer(customer_id)
        # Remove all uploaded ornament photos of this customer from disk
        for photo_path in photos:
            if photo_path and os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except OSError:
                    pass  # Non-fatal — record is already deleted from DB
    return redirect(url_for("customers"))

DEFAULT_DATASET_DIR = os.path.join(app.root_path, "Dataset")
DATASET_DIR = os.environ.get("DATASET_DIR", DEFAULT_DATASET_DIR)

# 🔥 SERVE DATASET IMAGES FROM LOCAL DATASET FOLDER OR CUSTOM PATH
@app.route("/dataset_image")
def dataset_image():
    path = request.args.get("path")
    category = request.args.get("category")
    item_id = request.args.get("item_id")

    # Try resolving candidate paths
    candidate_paths = []
    if category and item_id:
        candidate_paths.extend([
            os.path.join(DATASET_DIR, category, item_id, "1.webp"),
            os.path.join(DEFAULT_DATASET_DIR, category, item_id, "1.webp"),
            os.path.join(app.root_path, "static", "Dataset", category, item_id, "1.webp"),
        ])

    if path:
        candidate_paths.append(path)

    for p in candidate_paths:
        if p and os.path.exists(p):
            return send_file(p)

    return "Image not found", 404


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

