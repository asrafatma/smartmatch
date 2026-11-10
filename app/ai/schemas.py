from typing import List, Optional
from pydantic import BaseModel, Field

class AttributeDetails(BaseModel):
    color: List[str] = Field(default_factory=list, description="Primary and secondary colors")
    material: List[str] = Field(default_factory=list, description="Observed or stated materials")
    shape: List[str] = Field(default_factory=list, description="Shape characteristics")
    brand_or_logo: List[str] = Field(default_factory=list, description="Visible or stated brands/logos")
    distinctive_features: List[str] = Field(default_factory=list, description="Scratches, stickers, tags, unique patterns")

class ItemExtractionResult(BaseModel):
    object_type: str = Field(..., description="Specific item type, e.g. wallet, water bottle, backpack, smartphone")
    category: str = Field(
        ...,
        description="General category: electronics, personal_accessory, stationery, bag_backpack, clothing, key_id, bottle_container, other"
    )
    attributes: AttributeDetails = Field(default_factory=AttributeDetails)
    user_stated_details: List[str] = Field(
        default_factory=list,
        description="Details explicitly mentioned in the user description"
    )
    visually_observed_details: List[str] = Field(
        default_factory=list,
        description="Attributes reasonably verifiable from the photo"
    )
    unknowns: List[str] = Field(
        default_factory=list,
        description="Important attributes that cannot be determined"
    )
    image_quality: str = Field(
        default="adequate",
        description="Assessment of photo quality: high, adequate, poor, unreadable"
    )

class NormalizationResult(BaseModel):
    category: str
    object_type: str
    attributes: AttributeDetails
