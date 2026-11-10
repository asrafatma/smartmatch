import re

class Normalizer:
    # Synonym mappings for colors
    COLOR_SYNONYMS = {
        "navy": "dark_blue",
        "navy blue": "dark_blue",
        "dark blue": "dark_blue",
        "sky blue": "light_blue",
        "baby blue": "light_blue",
        "light blue": "light_blue",
        "blue": "blue",
        "crimson": "red",
        "scarlet": "red",
        "maroon": "dark_red",
        "burgundy": "dark_red",
        "red": "red",
        "charcoal": "dark_gray",
        "grey": "gray",
        "gray": "gray",
        "silver": "silver",
        "white": "white",
        "black": "black",
        "gold": "gold",
        "golden": "gold",
        "yellow": "yellow",
        "green": "green",
        "olive": "olive",
        "orange": "orange",
        "purple": "purple",
        "violet": "purple",
        "pink": "pink",
        "brown": "brown",
        "tan": "tan",
        "beige": "beige",
        "teal": "teal",
        "cyan": "cyan"
    }

    # Synonym mappings for materials
    MATERIAL_SYNONYMS = {
        "leather": "leather",
        "faux leather": "synthetic_leather",
        "pu leather": "synthetic_leather",
        "vegan leather": "synthetic_leather",
        "plastic": "plastic",
        "metal": "metal",
        "aluminum": "aluminum",
        "stainless steel": "stainless_steel",
        "steel": "steel",
        "canvas": "canvas",
        "fabric": "fabric",
        "cloth": "fabric",
        "nylon": "nylon",
        "polyester": "polyester",
        "denim": "denim",
        "glass": "glass",
        "wood": "wood",
        "rubber": "rubber",
        "silicone": "silicone",
        "paper": "paper",
        "cardboard": "paper"
    }

    # Synonym mappings for object types
    OBJECT_TYPE_SYNONYMS = {
        "wallet": "wallet",
        "billfold": "wallet",
        "purse": "wallet",
        "cardholder": "card_holder",
        "card holder": "card_holder",
        "money clip": "card_holder",
        "bottle": "water_bottle",
        "water bottle": "water_bottle",
        "hydro flask": "water_bottle",
        "flask": "water_bottle",
        "tumbler": "water_bottle",
        "thermos": "water_bottle",
        "mug": "cup_mug",
        "backpack": "backpack",
        "bookbag": "backpack",
        "knapsack": "backpack",
        "rucksack": "backpack",
        "tote bag": "tote_bag",
        "duffel": "duffel_bag",
        "duffel bag": "duffel_bag",
        "phone": "smartphone",
        "smartphone": "smartphone",
        "cell phone": "smartphone",
        "mobile": "smartphone",
        "iphone": "smartphone",
        "android": "smartphone",
        "laptop": "laptop",
        "notebook computer": "laptop",
        "macbook": "laptop",
        "chromebook": "laptop",
        "tablet": "tablet",
        "ipad": "tablet",
        "keys": "keys",
        "keychain": "keys",
        "car keys": "keys",
        "id card": "id_card",
        "student card": "id_card",
        "badge": "id_card",
        "notebook": "notebook",
        "journal": "notebook",
        "diary": "notebook",
        "binder": "notebook",
        "umbrella": "umbrella",
        "parasol": "umbrella",
        "glasses": "eyewear",
        "sunglasses": "eyewear",
        "spectacles": "eyewear",
        "headphones": "headphones",
        "earphones": "earbuds",
        "airpods": "earbuds",
        "earbuds": "earbuds"
    }

    # Synonym mappings for shapes
    SHAPE_SYNONYMS = {
        "rectangular": "rectangular",
        "rectangle": "rectangular",
        "square": "square",
        "cylindrical": "cylindrical",
        "cylinder": "cylindrical",
        "round": "round",
        "circular": "round",
        "oval": "oval",
        "foldable": "foldable",
        "bifold": "foldable",
        "trifold": "foldable",
        "flat": "flat",
        "compact": "compact"
    }

    # Category normalization
    CATEGORY_SYNONYMS = {
        "electronic": "electronics",
        "electronics": "electronics",
        "device": "electronics",
        "accessory": "personal_accessory",
        "accessories": "personal_accessory",
        "personal accessory": "personal_accessory",
        "personal_accessory": "personal_accessory",
        "stationery": "stationery",
        "office": "stationery",
        "bag": "bag_backpack",
        "backpack": "bag_backpack",
        "bag backpack": "bag_backpack",
        "bag_backpack": "bag_backpack",
        "clothing": "clothing",
        "apparel": "clothing",
        "key": "key_id",
        "keys": "key_id",
        "key id": "key_id",
        "key_id": "key_id",
        "id": "key_id",
        "bottle": "bottle_container",
        "bottle container": "bottle_container",
        "bottle_container": "bottle_container",
        "container": "bottle_container",
        "other": "other"
    }

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Strip punctuation, excessive whitespace, and lower-case."""
        if not text:
            return ""
        # Lowercase and replace hyphens/underscores with space
        cleaned = re.sub(r"[_\-]+", " ", str(text).lower().strip())
        # Remove unwanted punctuation
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def normalize_color(cls, color: str) -> str:
        cleaned = cls.clean_text(color)
        return cls.COLOR_SYNONYMS.get(cleaned, cleaned.replace(" ", "_"))

    @classmethod
    def normalize_material(cls, material: str) -> str:
        cleaned = cls.clean_text(material)
        return cls.MATERIAL_SYNONYMS.get(cleaned, cleaned.replace(" ", "_"))

    @classmethod
    def normalize_object_type(cls, obj_type: str) -> str:
        cleaned = cls.clean_text(obj_type)
        if not cleaned:
            return "item"
        if cleaned in cls.OBJECT_TYPE_SYNONYMS:
            return cls.OBJECT_TYPE_SYNONYMS[cleaned]
        # Check if any synonym key appears as a whole word phrase
        for syn, canonical in cls.OBJECT_TYPE_SYNONYMS.items():
            if re.search(rf"\b{re.escape(syn)}\b", cleaned):
                return canonical
        return cleaned.replace(" ", "_")

    @classmethod
    def normalize_shape(cls, shape: str) -> str:
        cleaned = cls.clean_text(shape)
        return cls.SHAPE_SYNONYMS.get(cleaned, cleaned.replace(" ", "_"))

    @classmethod
    def normalize_category(cls, category: str) -> str:
        cleaned = cls.clean_text(category)
        return cls.CATEGORY_SYNONYMS.get(cleaned, "other")

    @classmethod
    def normalize_list(cls, items: list, normalizer_func) -> list[str]:
        if not items or not isinstance(items, list):
            return []
        res = []
        for item in items:
            if item:
                norm = normalizer_func(str(item))
                if norm and norm not in res:
                    res.append(norm)
        return res

    @classmethod
    def normalize_attributes(cls, attributes: dict) -> dict:
        """Normalizes an entire attributes dictionary."""
        if not attributes or not isinstance(attributes, dict):
            return {
                "color": [],
                "material": [],
                "shape": [],
                "brand_or_logo": [],
                "distinctive_features": []
            }
        
        return {
            "color": cls.normalize_list(attributes.get("color", []), cls.normalize_color),
            "material": cls.normalize_list(attributes.get("material", []), cls.normalize_material),
            "shape": cls.normalize_list(attributes.get("shape", []), cls.normalize_shape),
            "brand_or_logo": cls.normalize_list(
                attributes.get("brand_or_logo", []),
                lambda x: cls.clean_text(x).replace(" ", "_")
            ),
            "distinctive_features": cls.normalize_list(
                attributes.get("distinctive_features", []),
                lambda x: cls.clean_text(x)
            ),
        }

    @classmethod
    def normalize_report(cls, report_data: dict) -> dict:
        """
        Takes raw report dictionary and normalizes category, object_type,
        and internal attributes.
        """
        report = dict(report_data)
        report["category"] = cls.normalize_category(report.get("category", "other"))
        
        raw_attrs = report.get("attributes", {})
        if not isinstance(raw_attrs, dict):
            raw_attrs = {}
        report["attributes"] = cls.normalize_attributes(raw_attrs)

        obj_type = raw_attrs.get("object_type") or report.get("object_type") or report.get("title", "")
        report["object_type"] = cls.normalize_object_type(obj_type)
        return report
