#!/usr/bin/env python3
"""
Archive Face Biometrics Enrollment Engine (enroll_archive_faces_onnx.py)
=======================================================================
Extracts 512-dimension normalized embeddings for confirmed ancestor portraits 
using the exported ONNX MobileFaceNet model and saves them to SQLite and a 
lightweight static JSON reference vector bank for in-browser client matching.
"""

import os
import sys
import json
import sqlite3
import numpy as np
from PIL import Image
import onnxruntime as ort

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "preservation_output", "genealogy_preservation.db")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "ancestor_face_embedder.onnx")
PUBLIC_JSON_PATH = os.path.join(PROJECT_ROOT, "frontend", "public", "api", "face_reference_bank.json")
DIST_JSON_PATH = os.path.join(PROJECT_ROOT, "frontend", "dist", "api", "face_reference_bank.json")

def preprocess_face(image_path, target_size=(112, 112)):
    """
    Load image, perform square center-crop preserving face aspect ratio, 
    resize to 112x112, and normalize to [-1.0, 1.0] in CHW float32 format.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            
            # Crop square focused on top-middle 80% (where historical portraits center the face)
            crop_size = min(w, h)
            left = (w - crop_size) // 2
            top = max(0, int((h - crop_size) * 0.25))
            right = left + crop_size
            bottom = min(h, top + crop_size)
            
            cropped = img.crop((left, top, right, bottom)).resize(target_size, Image.Resampling.LANCZOS)
            arr = np.array(cropped, dtype=np.float32)
            
            # Normalize to [-1.0, 1.0] (ArcFace / MobileFaceNet standard)
            arr = (arr - 127.5) / 128.0
            # HWC -> CHW -> NCHW
            tensor = np.transpose(arr, (2, 0, 1))
            tensor = np.expand_dims(tensor, axis=0)
            return tensor
    except Exception as e:
        return None

def enroll_faces():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"ONNX model not found at {MODEL_PATH}. Run scripts/train_export_face_onnx.py first.")

    print(f"=== Initializing ONNX Runtime Session ({MODEL_PATH}) ===")
    ort_session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    input_name = ort_session.get_inputs()[0].name

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Query confirmed candidate photos
    c.execute("""
        SELECT photo_id, primary_person_id, primary_person_name, local_image_path, document_type
        FROM photo_catalog
        WHERE primary_person_id IS NOT NULL 
          AND local_image_path IS NOT NULL
        ORDER BY photo_id ASC
    """)
    rows = c.fetchall()
    print(f"Discovered {len(rows)} candidate ancestor portraits with verified person IDs.")

    # Prepare directories
    os.makedirs(os.path.dirname(PUBLIC_JSON_PATH), exist_ok=True)
    if os.path.exists(os.path.dirname(DIST_JSON_PATH)):
        os.makedirs(os.path.dirname(DIST_JSON_PATH), exist_ok=True)

    enrolled_count = 0
    reference_bank = []

    # Clean existing onnx_mobilefacenet embeddings to avoid duplicate entries
    c.execute("DELETE FROM face_embeddings WHERE engine = 'onnx_mobilefacenet'")
    conn.commit()

    search_roots = [
        os.path.join(PROJECT_ROOT, "frontend", "public"),
        os.path.join(PROJECT_ROOT, "preservation_output"),
        PROJECT_ROOT
    ]

    for photo_id, person_id, person_name, rel_path, doc_type in rows:
        # Resolve path
        resolved_path = None
        for root in search_roots:
            candidate = os.path.join(root, rel_path.lstrip("/"))
            if os.path.isfile(candidate):
                resolved_path = candidate
                break

        if not resolved_path:
            continue

        tensor = preprocess_face(resolved_path)
        if tensor is None:
            continue

        # Run ONNX inference
        outputs = ort_session.run(None, {input_name: tensor})
        embedding = outputs[0][0]  # Shape (512,)
        
        # Ensure L2 norm = 1.0
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        vector_list = embedding.tolist()
        vector_json = json.dumps(vector_list)

        # Store in SQLite database
        c.execute("""
            INSERT INTO face_embeddings 
            (photo_id, person_id, person_name, image_path, face_index, bounding_box, embedding_vector, engine, is_confirmed_reference)
            VALUES (?, ?, ?, ?, 0, ?, ?, 'onnx_mobilefacenet', 1)
        """, (photo_id, person_id, person_name, rel_path, json.dumps({"top": 0, "left": 0, "bottom": 112, "right": 112}), vector_json))

        reference_bank.append({
            "photo_id": photo_id,
            "person_id": person_id,
            "name": person_name,
            "image_path": rel_path,
            "document_type": doc_type or "portrait",
            "vector": [round(v, 5) for v in vector_list]
        })

        enrolled_count += 1
        if enrolled_count % 100 == 0:
            print(f"Enrolled {enrolled_count} ancestor facial vectors...")

    conn.commit()
    conn.close()

    print(f"\nSuccessfully enrolled {enrolled_count} ancestor reference vectors into SQLite.")

    # Write static reference vector bank JSON for in-browser client inference
    with open(PUBLIC_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(reference_bank, f)
    print(f"Exported client reference bank: {PUBLIC_JSON_PATH} ({os.path.getsize(PUBLIC_JSON_PATH) / (1024 * 1024):.2f} MB)")

    if os.path.exists(os.path.dirname(DIST_JSON_PATH)):
        with open(DIST_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(reference_bank, f)
        print(f"Copied to distribution build: {DIST_JSON_PATH}")

if __name__ == "__main__":
    enroll_faces()
