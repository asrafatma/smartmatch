from datetime import datetime
from typing import List, Dict, Any, Tuple
from app.ai.normalizer import Normalizer
from app.config import Config
from app.repositories.report_repository import ReportRepository
from app.repositories.match_repository import MatchRepository

class MatchingEngine:
    ALGORITHM_VERSION = Config.ALGORITHM_VERSION
    CONFIG_VERSION = Config.CONFIG_VERSION
    WEIGHTS = Config.MATCHING_WEIGHTS

    @classmethod
    def compare_reports(cls, base_report: Dict[str, Any], candidate_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates a deterministic 100-point match score between two reports
        (typically one Lost and one Found).
        """
        norm_base = Normalizer.normalize_report(base_report)
        norm_cand = Normalizer.normalize_report(candidate_report)

        score_breakdown: Dict[str, float] = {}
        matched_attributes: List[str] = []
        conflicts: List[str] = []
        unknowns: List[str] = []

        # 1. Category Compatibility (Weight: 20)
        max_cat = cls.WEIGHTS["category"]
        base_cat = norm_base.get("category", "other")
        cand_cat = norm_cand.get("category", "other")
        
        if base_cat == cand_cat and base_cat != "other":
            score_breakdown["category"] = max_cat
            matched_attributes.append(f"Identical category: {base_cat.replace('_', ' ').title()}")
        elif base_cat == "other" or cand_cat == "other":
            score_breakdown["category"] = max_cat * 0.5
            unknowns.append("Generic or unclassified category")
        else:
            score_breakdown["category"] = 0.0
            conflicts.append(f"Category mismatch: {base_cat.replace('_', ' ')} vs {cand_cat.replace('_', ' ')}")

        # 2. Object Type (Weight: 15)
        max_obj = cls.WEIGHTS["object_type"]
        base_obj = norm_base.get("object_type", "")
        cand_obj = norm_cand.get("object_type", "")

        if base_obj and cand_obj and base_obj == cand_obj:
            score_breakdown["object_type"] = max_obj
            matched_attributes.append(f"Matching object type: {base_obj.replace('_', ' ').title()}")
        elif base_obj in cand_obj or cand_obj in base_obj:
            score_breakdown["object_type"] = max_obj * 0.7
            matched_attributes.append(f"Partially matching object type ({base_obj} ~ {cand_obj})")
        elif not base_obj or not cand_obj or base_obj == "item" or cand_obj == "item":
            score_breakdown["object_type"] = max_obj * 0.35
            unknowns.append("Specific object type could not be strictly determined")
        else:
            score_breakdown["object_type"] = 0.0
            conflicts.append(f"Object type difference: {base_obj} vs {cand_obj}")

        # 3. Brand / Logo (Weight: 15)
        max_brand = cls.WEIGHTS["brand_or_logo"]
        b_brands = set(norm_base.get("attributes", {}).get("brand_or_logo", []))
        c_brands = set(norm_cand.get("attributes", {}).get("brand_or_logo", []))

        if b_brands and c_brands:
            shared_brands = b_brands.intersection(c_brands)
            if shared_brands:
                score_breakdown["brand_or_logo"] = max_brand
                matched_attributes.append(f"Matching brand/logo: {', '.join(sorted(shared_brands))}")
            else:
                score_breakdown["brand_or_logo"] = 0.0
                conflicts.append(f"Distinct brands recorded ({', '.join(b_brands)} vs {', '.join(c_brands)})")
        elif not b_brands and not c_brands:
            score_breakdown["brand_or_logo"] = max_brand * 0.5
            unknowns.append("No brand or logo visible or stated on either report")
        else:
            # One has brand, other is unbranded/unknown
            score_breakdown["brand_or_logo"] = max_brand * 0.5
            unknowns.append("Brand visible or stated on one report, but absent or unreadable on the other")

        # 4. Color (Weight: 15)
        max_color = cls.WEIGHTS["color"]
        b_colors = set(norm_base.get("attributes", {}).get("color", []))
        c_colors = set(norm_cand.get("attributes", {}).get("color", []))

        # Filter out generic 'unknown'
        b_colors.discard("unknown")
        c_colors.discard("unknown")

        if b_colors and c_colors:
            shared_colors = b_colors.intersection(c_colors)
            if shared_colors:
                score_breakdown["color"] = max_color
                matched_attributes.append(f"Matching color(s): {', '.join(sorted(shared_colors))}")
            else:
                score_breakdown["color"] = 0.0
                conflicts.append(f"Different color descriptions ({', '.join(b_colors)} vs {', '.join(c_colors)})")
        elif not b_colors and not c_colors:
            score_breakdown["color"] = max_color * 0.5
            unknowns.append("Color is unknown on both reports")
        else:
            score_breakdown["color"] = max_color * 0.5
            unknowns.append("Color reported on one report but unverified on the other")

        # 5. Material & Shape (Weight: 10 => 5 for material, 5 for shape)
        max_mat_shape = cls.WEIGHTS["material_and_shape"]
        half_ms = max_mat_shape / 2.0
        mat_pts = 0.0
        shape_pts = 0.0

        b_mat = set(norm_base.get("attributes", {}).get("material", []))
        c_mat = set(norm_cand.get("attributes", {}).get("material", []))
        if b_mat and c_mat:
            if b_mat.intersection(c_mat):
                mat_pts = half_ms
                matched_attributes.append(f"Matching material: {', '.join(b_mat.intersection(c_mat))}")
            else:
                mat_pts = 0.0
                conflicts.append(f"Material difference ({', '.join(b_mat)} vs {', '.join(c_mat)})")
        else:
            mat_pts = half_ms * 0.5
            unknowns.append("Material not specified on one or both reports")

        b_shape = set(norm_base.get("attributes", {}).get("shape", []))
        c_shape = set(norm_cand.get("attributes", {}).get("shape", []))
        if b_shape and c_shape:
            if b_shape.intersection(c_shape):
                shape_pts = half_ms
                matched_attributes.append(f"Matching shape: {', '.join(b_shape.intersection(c_shape))}")
            else:
                shape_pts = 0.0
                conflicts.append(f"Shape difference ({', '.join(b_shape)} vs {', '.join(c_shape)})")
        else:
            shape_pts = half_ms * 0.5
            unknowns.append("Shape not specified on one or both reports")

        score_breakdown["material_and_shape"] = round(mat_pts + shape_pts, 2)

        # 6. Distinctive Features (Weight: 15)
        max_feat = cls.WEIGHTS["distinctive_features"]
        b_feat = [f.lower() for f in norm_base.get("attributes", {}).get("distinctive_features", [])]
        c_feat = [f.lower() for f in norm_cand.get("attributes", {}).get("distinctive_features", [])]

        b_text = " ".join(b_feat) + " " + norm_base.get("description", "").lower()
        c_text = " ".join(c_feat) + " " + norm_cand.get("description", "").lower()

        # Check keyword overlaps in features
        key_terms = ["sticker", "scratched", "scratch", "broken", "engraved", "engraving", "keychain", "tag", "stitched", "zipper", "strap", "case", "cover", "charm"]
        shared_terms = [t for t in key_terms if (t in b_text and t in c_text)]

        if shared_terms:
            score_breakdown["distinctive_features"] = max_feat
            matched_attributes.append(f"Shared distinctive characteristic: {', '.join(shared_terms)}")
        elif not b_feat and not c_feat:
            score_breakdown["distinctive_features"] = max_feat * 0.5
            unknowns.append("No distinctive features recorded")
        else:
            score_breakdown["distinctive_features"] = max_feat * 0.35
            unknowns.append("Distinctive features reported on one item but not observed on the other")

        # 7. Location Proximity (Weight: 5)
        max_loc = cls.WEIGHTS["location"]
        b_loc = norm_base.get("location", "").strip().lower()
        c_loc = norm_cand.get("location", "").strip().lower()

        if b_loc and c_loc and (b_loc == c_loc):
            score_breakdown["location"] = float(max_loc)
            matched_attributes.append(f"Identical reported location: '{norm_base.get('location')}'")
        elif b_loc and c_loc and (b_loc in c_loc or c_loc in b_loc):
            score_breakdown["location"] = max_loc * 0.8
            matched_attributes.append(f"Adjacent or related location: '{b_loc}' ~ '{c_loc}'")
        elif not b_loc or not c_loc:
            score_breakdown["location"] = max_loc * 0.5
            unknowns.append("Location details incomplete")
        else:
            score_breakdown["location"] = max_loc * 0.4
            unknowns.append(f"Different campus locations: '{b_loc}' vs '{c_loc}'")

        # 8. Date Proximity (Weight: 5)
        max_date = cls.WEIGHTS["date"]
        date_pts, date_msg = cls._calculate_date_score(
            norm_base.get("incident_date"),
            norm_cand.get("incident_date"),
            max_date
        )
        score_breakdown["date"] = date_pts
        if date_msg:
            if "Within" in date_msg or "Same" in date_msg:
                matched_attributes.append(date_msg)
            elif "exceeds" in date_msg:
                conflicts.append(date_msg)
            else:
                unknowns.append(date_msg)

        # Sum total score and round
        total_score = round(sum(score_breakdown.values()), 1)
        total_score = max(0.0, min(100.0, total_score))

        # Categorize label
        if total_score >= Config.STRONG_MATCH_THRESHOLD:
            label = "Strong candidate"
        elif total_score >= Config.POSSIBLE_MATCH_THRESHOLD:
            label = "Possible match"
        else:
            label = "Low similarity"

        return {
            "score": total_score,
            "label": label,
            "score_breakdown": score_breakdown,
            "matched_attributes": matched_attributes,
            "conflicts": conflicts,
            "unknowns": unknowns,
            "algorithm_version": cls.ALGORITHM_VERSION,
            "config_version": cls.CONFIG_VERSION
        }

    @classmethod
    def _calculate_date_score(cls, date1_str: Any, date2_str: Any, max_pts: float) -> Tuple[float, str]:
        if not date1_str or not date2_str:
            return max_pts * 0.5, "Date information not fully specified"

        try:
            d1 = cls._parse_date(date1_str)
            d2 = cls._parse_date(date2_str)
            diff_days = abs((d1 - d2).days)

            if diff_days == 0:
                return float(max_pts), "Same incident date"
            elif diff_days <= 2:
                return max_pts * 0.9, f"Within {diff_days} day(s) difference"
            elif diff_days <= 7:
                return max_pts * 0.7, f"Within {diff_days} days difference"
            elif diff_days <= 14:
                return max_pts * 0.4, f"{diff_days} days difference"
            else:
                return 0.0, f"Date difference exceeds {diff_days} days"
        except Exception:
            return max_pts * 0.5, "Date format could not be verified"

    @classmethod
    def _parse_date(cls, val: Any) -> datetime:
        if isinstance(val, datetime):
            return val
        s = str(val)[:10]
        return datetime.strptime(s, "%Y-%m-%d")

    @classmethod
    def find_matches_for_report(cls, report_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Runs deterministic matching for a specific report against all opposite-type
        active reports, sorts by score descending with tie-breakers, and persists results.
        """
        base_report = ReportRepository.find_by_id(report_id)
        if not base_report:
            return []

        # Only compare active reports
        if base_report.get("status") not in ("active", "claim_pending", "under_review"):
            return []

        base_type = base_report.get("report_type")
        target_type = "found" if base_type == "lost" else "lost"

        # Fetch candidate active reports
        candidates = ReportRepository.find_active_by_type(target_type)

        results = []
        for cand in candidates:
            cand_id = cand["id"]
            if cand_id == report_id:
                continue

            match_data = cls.compare_reports(base_report, cand)
            
            # Determine lost and found IDs for storage
            lost_id = report_id if base_type == "lost" else cand_id
            found_id = cand_id if base_type == "lost" else report_id

            record = {
                "lost_report_id": lost_id,
                "found_report_id": found_id,
                "score": match_data["score"],
                "label": match_data["label"],
                "score_breakdown": match_data["score_breakdown"],
                "matched_attributes": match_data["matched_attributes"],
                "conflicts": match_data["conflicts"],
                "unknowns": match_data["unknowns"],
                "algorithm_version": match_data["algorithm_version"],
                "config_version": match_data["config_version"],
                "candidate_report": cand
            }
            
            # Save or update in matches repository
            MatchRepository.save_match(record)
            results.append(record)

        # Deterministic Tie-breaking:
        # 1. Score descending
        # 2. Incident-date proximity ascending (closest dates first)
        # 3. Creation date ascending
        # 4. Stable report ID ascending
        def sort_key(item):
            cand = item["candidate_report"]
            score = item["score"]
            # calculate date diff
            try:
                base_d = cls._parse_date(base_report.get("incident_date"))
                cand_d = cls._parse_date(cand.get("incident_date"))
                date_diff = abs((base_d - cand_d).days)
            except Exception:
                date_diff = 9999
            created_at = str(cand.get("created_at", ""))
            c_id = str(cand.get("id", ""))
            return (-score, date_diff, created_at, c_id)

        results.sort(key=sort_key)
        return results[:limit]
