#!/usr/bin/env python3
"""
scripts/onnx_archive_pipeline.py

Production-Grade ONNX Archival Sorting, Ingestion, OCR & Biometric Pipeline
=============================================================================
Integrates:
1. SCRFD-2.5G ONNX: 5-point facial landmark detection and affine pose alignment.
2. PP-OCRv4 (Det + Rec) ONNX: Real-time document, obituary, and headstone transcription.
3. Multi-Modal Asset Triage: Classifies assets into portrait, headstone, typed_document, or manuscript.
4. Genealogical Entity Matching: Disambiguates extracted names/dates against 3,793 profiles.
5. GPS Level 3/4 Data Integrity: Staging via asset_proposals & audit_flags with human-in-the-loop promotion.
"""

import os
import sys
import json
import sqlite3
import hashlib
import re
from datetime import datetime
import numpy as np
import cv2
import onnxruntime as ort

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DB_PATH = os.path.join(PROJECT_ROOT, "preservation_output", "genealogy_preservation.db")

class SCRFDFaceDetector:
    def __init__(self, model_path=os.path.join(MODELS_DIR, "scrfd_2.5g_bnkps.onnx")):
        self.session = ort.InferenceSession(model_path)
        self.target_size = 640
        self.strides = [8, 16, 32]

    def detect(self, img_bgr, score_thresh=0.45, nms_thresh=0.4):
        h, w = img_bgr.shape[:2]
        scale = self.target_size / max(h, w)
        nh, nw = int(h * scale), int(w * scale)
        resized = cv2.resize(img_bgr, (nw, nh))

        padded = np.zeros((self.target_size, self.target_size, 3), dtype=np.uint8)
        padded[:nh, :nw] = resized

        blob = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32)
        blob = (blob - 127.5) / 128.0
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis, ...]

        outputs = self.session.run(None, {'input.1': blob})
        scores_list = [outputs[0], outputs[1], outputs[2]]
        bboxes_list = [outputs[3], outputs[4], outputs[5]]
        kps_list = [outputs[6], outputs[7], outputs[8]]

        detections = []
        for idx, stride in enumerate(self.strides):
            feat_h = self.target_size // stride
            feat_w = self.target_size // stride
            anchor_centers = np.stack(np.mgrid[:feat_h, :feat_w][::-1], axis=-1).astype(np.float32)
            anchor_centers = (anchor_centers * stride).reshape((-1, 2))
            anchor_centers = np.repeat(anchor_centers, 2, axis=0)

            scores = scores_list[idx]
            bboxes = bboxes_list[idx]
            kps = kps_list[idx]

            pos_idx = np.where(scores[:, 0] > score_thresh)[0]
            for p in pos_idx:
                score = float(scores[p, 0])
                cx, cy = anchor_centers[p]
                x1 = (cx - bboxes[p, 0] * stride) / scale
                y1 = (cy - bboxes[p, 1] * stride) / scale
                x2 = (cx + bboxes[p, 2] * stride) / scale
                y2 = (cy + bboxes[p, 3] * stride) / scale

                raw_kps = kps[p].reshape((5, 2))
                pred_kps = (anchor_centers[p] + raw_kps * stride) / scale
                detections.append({'score': score, 'bbox': [x1, y1, x2, y2], 'kps': pred_kps})

        # NMS
        if not detections:
            return []
        
        boxes_arr = np.array([d['bbox'] for d in detections])
        scores_arr = np.array([d['score'] for d in detections])
        x1 = boxes_arr[:, 0]
        y1 = boxes_arr[:, 1]
        x2 = boxes_arr[:, 2]
        y2 = boxes_arr[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores_arr.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w_ov = np.maximum(0.0, xx2 - xx1 + 1)
            h_ov = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w_ov * h_ov
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(ovr <= nms_thresh)[0]
            order = order[inds + 1]

        return [detections[k] for k in keep]

    def align_face_112(self, img_bgr, kps):
        """Standard ArcFace 112x112 5-point affine alignment."""
        ref_pts = np.array([
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041]
        ], dtype=np.float32)

        M, inliers = cv2.estimateAffinePartial2D(kps.astype(np.float32), ref_pts)
        if M is None:
            # Fallback center crop
            x1, y1 = int(kps[:, 0].min()), int(kps[:, 1].min())
            x2, y2 = int(kps[:, 0].max()), int(kps[:, 1].max())
            crop = img_bgr[max(0, y1):min(img_bgr.shape[0], y2), max(0, x1):min(img_bgr.shape[1], x2)]
            return cv2.resize(crop, (112, 112))
        
        warped = cv2.warpAffine(img_bgr, M, (112, 112), borderValue=0.0)
        return warped


class PPOCRTextEngine:
    def __init__(self, 
                 det_path=os.path.join(MODELS_DIR, "ppocrv4_det.onnx"),
                 rec_path=os.path.join(MODELS_DIR, "ppocrv4_rec.onnx"),
                 dict_path=os.path.join(MODELS_DIR, "en_dict.txt")):
        self.det_sess = ort.InferenceSession(det_path)
        self.rec_sess = ort.InferenceSession(rec_path)
        
        with open(dict_path, 'r', encoding='utf-8') as f:
            chars = [line.strip('\r\n') for line in f]
        self.vocab = ['<blank>'] + chars + [' ']

    def detect_boxes(self, img_bgr, max_side=960, thresh=0.38):
        h, w = img_bgr.shape[:2]
        scale = max_side / max(h, w)
        nh = int(round(h * scale / 32) * 32)
        nw = int(round(w * scale / 32) * 32)
        resized = cv2.resize(img_bgr, (nw, nh))

        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        blob = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = (blob - mean) / std
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

        pred = self.det_sess.run(None, {'x': blob})[0][0, 0]
        text_mask = (pred > thresh).astype(np.uint8)
        contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for c in contours:
            if cv2.contourArea(c) < 60:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            ox1 = int(x / (nw / w))
            oy1 = int(y / (nh / h))
            ox2 = int((x + bw) / (nw / w))
            oy2 = int((y + bh) / (nh / h))
            boxes.append((oy1, ox1, oy2, ox2))

        # Sort roughly top-to-bottom, left-to-right
        boxes.sort(key=lambda b: (b[0] // 25, b[1]))
        return boxes

    def recognize_crop(self, crop_bgr):
        ch, cw = crop_bgr.shape[:2]
        if ch < 5 or cw < 8:
            return "", 0.0

        target_h = 48
        target_w = max(48, int(cw * (target_h / ch)))
        target_w = int(round(target_w / 4) * 4)
        crop_resized = cv2.resize(crop_bgr, (target_w, target_h))

        blob = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = (blob - 0.5) / 0.5
        blob = np.transpose(blob, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

        out = self.rec_sess.run(None, {'x': blob})[0]
        preds = np.argmax(out[0], axis=-1)
        probs = np.max(out[0], axis=-1)

        text = []
        char_confidences = []
        last_idx = 0
        for p, conf in zip(preds, probs):
            if p != 0 and p != last_idx and p < len(self.vocab):
                text.append(self.vocab[p])
                char_confidences.append(float(conf))
            last_idx = p

        line_str = ''.join(text).strip()
        avg_conf = float(np.mean(char_confidences)) if char_confidences else 0.0
        return line_str, avg_conf

    def transcribe_image(self, img_bgr):
        boxes = self.detect_boxes(img_bgr)
        h, w = img_bgr.shape[:2]
        results = []
        for (y1, x1, y2, x2) in boxes:
            pad = 2
            crop = img_bgr[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
            if crop.size == 0:
                continue
            line_txt, conf = self.recognize_crop(crop)
            if line_txt:
                results.append({
                    "bbox": [x1, y1, x2, y2],
                    "text": line_txt,
                    "confidence": round(conf, 3)
                })
        return results


class AssetTriageClassifier:
    """Triage incoming media into portrait, headstone, typed_document, or manuscript."""
    def __init__(self, face_detector, ocr_engine):
        self.face_detector = face_detector
        self.ocr_engine = ocr_engine

    def triage(self, img_bgr, filename=""):
        faces = self.face_detector.detect(img_bgr)
        ocr_lines = self.ocr_engine.transcribe_image(img_bgr)

        fn = filename.lower()
        full_text = " ".join([l['text'] for l in ocr_lines]).lower()

        # Check headstone cues
        headstone_keywords = ['cemetery', 'grave', 'tomb', 'in memory', 'departed', 'aged', 'years', 'born', 'died']
        headstone_hits = sum(1 for kw in headstone_keywords if kw in full_text or kw in fn)
        if "tombstone" in fn or "cem" in fn or headstone_hits >= 3 and len(faces) == 0:
            return "headstone", 0.92, faces, ocr_lines

        # Check portrait cues
        if len(faces) >= 1 and len(ocr_lines) <= 4:
            return "portrait", 0.95, faces, ocr_lines

        # Check document cues
        if len(ocr_lines) >= 3 or "obit" in fn or "census" in fn or "doc" in fn:
            # Differentiate typed vs manuscript
            if "bible" in fn or "will" in fn or "deed" in fn or "hand" in fn:
                return "handwritten_manuscript", 0.88, faces, ocr_lines
            return "typed_document", 0.93, faces, ocr_lines

        # Default fallback
        if len(faces) > 0:
            return "portrait", 0.75, faces, ocr_lines
        return "typed_document", 0.65, faces, ocr_lines


class GenealogicalEntityMatcher:
    """Matches OCR text or portraits against 3,793 persons in SQLite."""
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._load_cache()

    def _load_cache(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT person_id, name, first_name, maiden_name, married_last_name, 
                   birth_info, death_info, notes
            FROM persons
        """)
        self.persons = c.fetchall()
        conn.close()

    def match_entities(self, text, filename=""):
        if not text and not filename:
            return None, 0.0, "No text extracted", []

        combined_text = f"{filename.replace('_', ' ').replace('-', ' ')} {text}"
        clean_text = " ".join(combined_text.split())
        t_lower = clean_text.lower()
        years = [int(y) for y in re.findall(r'\b(1[789]\d\d|20\d\d)\b', clean_text)]
        
        GEOGRAPHIC_STOPWORDS = {'new york', 'delaware', 'maryland', 'new jersey', 'pennsylvania', 'united states', 'north carolina', 'virginia'}

        best_pid = None
        best_score = 0.0
        best_reasoning = ""
        proposed_facts = []

        for p in self.persons:
            pid, name, fn, mn, mln, b_info, d_info, notes = p
            p_name = name.lower().strip()
            if p_name in GEOGRAPHIC_STOPWORDS:
                continue

            score = 0.0
            reasons = []

            p_name = name.lower().strip()
            name_parts = [part for part in p_name.split() if len(part) >= 3]

            # Require multi-token match or full exact string match
            if len(name_parts) >= 2 and p_name in t_lower:
                score += 0.85
                reasons.append(f"Full name '{name}' exact match in document & metadata")
            elif fn and mln and fn.lower() != mln.lower() and len(fn) >= 3 and len(mln) >= 3 and fn.lower() in t_lower and mln.lower() in t_lower:
                score += 0.80
                reasons.append(f"Both First ('{fn}') and Surname ('{mln}') matched in document")
            elif len(name_parts) == 1 and name_parts[0] in t_lower:
                # Single-token penalty: only slight score, cannot match alone
                score += 0.10

            # If no name match at all, skip
            if score < 0.10:
                continue

            # Year match bonus
            if years:
                p_years = [int(y) for y in re.findall(r'\b(1[789]\d\d|20\d\d)\b', f"{b_info} {d_info} {notes}")]
                matched_yrs = set(years).intersection(set(p_years))
                if matched_yrs:
                    score += 0.20
                    reasons.append(f"Contemporaneous vital years {list(matched_yrs)} matched")

            # Place match bonus
            delmarva_places = ['delaware', 'kent', 'sussex', 'salem', 'cumberland', 'millsboro', 'cheswold', 'dover', 'milford']
            matched_places = [pl for pl in delmarva_places if pl in t_lower and pl in str(notes).lower()]
            if matched_places:
                score += 0.10
                reasons.append(f"Delmarva place match: {matched_places}")

            # Cluster / surname tie bonus
            if mln and mln.lower() in str(notes).lower():
                score += 0.05

            if score > best_score:
                best_score = score
                best_pid = pid
                best_reasoning = "; ".join(reasons)

        if best_pid and best_score >= 0.50:
            # Propose facts
            if years:
                # If "died" or "obit" in text, propose death
                if "died" in clean_text.lower() or "obit" in clean_text.lower() or "funeral" in clean_text.lower():
                    proposed_facts.append({
                        "fact_type": "Death",
                        "date_string": str(years[-1]),
                        "place_string": "Delmarva",
                        "value_string": f"Death documented in primary record ({years[-1]})"
                    })
                if "born" in clean_text.lower():
                    proposed_facts.append({
                        "fact_type": "Birth",
                        "date_string": str(years[0]),
                        "place_string": "Delmarva",
                        "value_string": f"Birth documented in primary record ({years[0]})"
                    })
            proposed_facts.append({
                "fact_type": "Document Mention",
                "value_string": f"Primary transcription assertion: {clean_text[:120]}..."
            })

        return best_pid, round(best_score, 3), best_reasoning, proposed_facts


class AssetProposalManager:
    """Manages ingestion, staging, audit flagging, and GPS Level 3 proposal promotion."""
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.face_detector = SCRFDFaceDetector()
        self.ocr_engine = PPOCRTextEngine()
        self.triage = AssetTriageClassifier(self.face_detector, self.ocr_engine)
        self.entity_matcher = GenealogicalEntityMatcher(db_path)

    def ingest_file(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Compute SHA-256 for integrity
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        img_bgr = cv2.imread(file_path)
        if img_bgr is None:
            raise ValueError(f"Failed to decode image: {file_path}")

        filename = os.path.basename(file_path)
        asset_type, triage_conf, faces, ocr_lines = self.triage.triage(img_bgr, filename)

        full_text = "\n".join([l['text'] for l in ocr_lines])
        bboxes = json.dumps([l['bbox'] for l in ocr_lines]) if ocr_lines else json.dumps([f['bbox'] for f in faces])

        matched_pid, match_conf, match_reasoning, proposed_facts = self.entity_matcher.match_entities(full_text, filename)

        model_meta = json.dumps({
            "face_detector": "scrfd_2.5g_bnkps.onnx",
            "ocr_det": "ppocrv4_det.onnx",
            "ocr_rec": "ppocrv4_rec.onnx",
            "face_count": len(faces),
            "text_line_count": len(ocr_lines),
            "timestamp": datetime.now().isoformat()
        })

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO asset_proposals 
            (file_path, file_sha256, asset_type, triage_confidence, extracted_text, 
             bounding_boxes, matched_person_id, match_confidence, match_reasoning, 
             proposed_facts, model_metadata, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (file_path, file_hash, asset_type, triage_conf, full_text, bboxes,
              matched_pid, match_conf, match_reasoning, json.dumps(proposed_facts), model_meta))
        proposal_id = c.lastrowid

        # Flag ambiguous matches for human review in audit_flags
        if matched_pid and 0.50 <= match_conf < 0.90:
            c.execute("""
                INSERT INTO audit_flags (category, severity, person_id, description, evidence)
                VALUES ('AI Proposal Ambiguity', 'warning', ?, ?, ?)
            """, (matched_pid, f"Ambiguous ONNX asset match ({int(match_conf*100)}%) for {filename}",
                  f"Proposal #{proposal_id}: {match_reasoning}"))

        conn.commit()
        conn.close()

        return {
            "proposal_id": proposal_id,
            "file": filename,
            "asset_type": asset_type,
            "triage_confidence": triage_conf,
            "matched_person_id": matched_pid,
            "match_confidence": match_conf,
            "reasoning": match_reasoning,
            "extracted_lines": len(ocr_lines),
            "proposed_facts": proposed_facts
        }

    def promote_proposal(self, proposal_id, reviewer_id="Archivist"):
        """Converts an approved proposal into ground truth facts + GPS Level 3 citations."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM asset_proposals WHERE proposal_id = ?", (proposal_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Proposal #{proposal_id} not found.")

        pid = row[7] # matched_person_id
        if not pid:
            conn.close()
            raise ValueError(f"Proposal #{proposal_id} has no matched person_id to promote to.")

        proposed_facts = json.loads(row[10]) if row[10] else []
        file_path = row[1]
        extracted_text = row[5] or ""
        fn = os.path.basename(file_path)

        # Create or fetch source record for this document
        c.execute("SELECT source_id FROM sources WHERE url = ?", (file_path,))
        src_row = c.fetchone()
        if src_row:
            src_id = src_row[0]
        else:
            c.execute("""
                INSERT INTO sources (title, url, dataset)
                VALUES (?, ?, 'primary_archive_ingest')
            """, (f"Archival Document Record: {fn}", file_path))
            src_id = c.lastrowid

        for pf in proposed_facts:
            c.execute("""
                INSERT INTO facts (person_id, fact_type, date_string, place_string, value_string)
                VALUES (?, ?, ?, ?, ?)
            """, (pid, pf.get("fact_type"), pf.get("date_string"), pf.get("place_string"), pf.get("value_string")))
            fact_id = c.lastrowid

            # GPS Level 3 Citation
            evidence_snippet = extracted_text.replace("\n", " ").strip()[:180]
            c.execute("""
                INSERT INTO citations (fact_id, source_id, evidence_text)
                VALUES (?, ?, ?)
            """, (fact_id, src_id, f"ONNX Transcription Verified: '{evidence_snippet}' (Document: {fn})"))

        # Mark proposal approved
        now = datetime.now().isoformat()
        c.execute("""
            UPDATE asset_proposals
            SET status = 'approved', reviewed_by = ?, reviewed_at = ?
            WHERE proposal_id = ?
        """, (reviewer_id, now, proposal_id))

        conn.commit()
        conn.close()
        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ONNX Archival Ingestion & Transcription Engine")
    subparsers = parser.add_subparsers(dest="command")

    ingest_p = subparsers.add_parser("ingest", help="Ingest a single file")
    ingest_p.add_argument("file_path", help="Path to image or document")

    batch_p = subparsers.add_parser("batch", help="Batch ingest a folder")
    batch_p.add_argument("folder_path", help="Path to directory containing assets")

    promote_p = subparsers.add_parser("promote", help="Promote proposal to ground truth facts")
    promote_p.add_argument("proposal_id", type=int, help="ID of proposal to approve")
    promote_p.add_argument("--reviewer", default="Archivist", help="Reviewer identifier")

    list_p = subparsers.add_parser("list", help="List pending proposals")

    args = parser.parse_args()

    manager = AssetProposalManager()

    if args.command == "ingest":
        res = manager.ingest_file(args.file_path)
        print(json.dumps(res, indent=2))
    elif args.command == "batch":
        import glob
        files = glob.glob(os.path.join(args.folder_path, "*.*"))
        print(f"Batch processing {len(files)} assets in {args.folder_path}...")
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                try:
                    res = manager.ingest_file(f)
                    print(f"✓ {res['file']} -> {res['asset_type']} | Match: Person #{res['matched_person_id']} ({int(res['match_confidence']*100)}%)")
                except Exception as e:
                    print(f"✗ Failed {f}: {e}")
    elif args.command == "promote":
        manager.promote_proposal(args.proposal_id, args.reviewer)
        print(f"Proposal #{args.proposal_id} approved and promoted to ground-truth facts & citations.")
    elif args.command == "list":
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT proposal_id, file_path, asset_type, matched_person_id, match_confidence, status FROM asset_proposals")
        for r in c.fetchall():
            print(f"Proposal #{r[0]}: {os.path.basename(r[1])} | {r[2]} -> Person #{r[3]} ({int(r[4]*100)}%) [{r[5]}]")
        conn.close()
    else:
        parser.print_help()
