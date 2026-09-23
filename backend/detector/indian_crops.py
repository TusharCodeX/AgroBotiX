"""
Indian Agricultural Botanical & Agronomic Profiles.
Defines crop-specific botanical contexts, associated weed species (grasses, sedges, broadleaves),
growth stages, and agronomic crop safety margins tailored to Indian field conditions.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class WeedSpeciesProfile:
    scientific_name: str
    common_name_en: str
    common_name_hi: str
    weed_type: str  # "grass", "sedge", "broadleaf"
    morphology: str  # "erect", "prostrate", "creeping", "tufted"
    danger_level: str  # "high", "medium", "critical"
    typical_height_cm: float
    description: str


@dataclass
class IndianCropProfile:
    context_id: str
    crop_name: str
    scientific_name: str
    season: str  # "kharif", "rabi", "zaid", "perennial"
    soil_types: List[str]
    default_safety_buffer_cm: float
    key_weeds: List[WeedSpeciesProfile]
    target_crops: List[str] = field(default_factory=list)


# Comprehensive Knowledge Base of Indian Crops and Weeds
INDIAN_CROP_PROFILES: Dict[str, IndianCropProfile] = {
    "rice": IndianCropProfile(
        context_id="rice",
        crop_name="Rice (Paddy)",
        scientific_name="Oryza sativa",
        season="kharif",
        soil_types=["Clayey loam", "Alluvial", "Waterlogged mud", "Drying cracked clay"],
        default_safety_buffer_cm=6.0,
        key_weeds=[
            WeedSpeciesProfile("Echinochloa crus-galli", "Barnyard Grass", "Sanwak", "grass", "erect", "critical", 60.0, "Major mimic weed in direct-seeded and transplanted rice"),
            WeedSpeciesProfile("Echinochloa colona", "Jungle Rice", "Shama", "grass", "erect", "critical", 45.0, "Highly competitive grass weed in early paddy stages"),
            WeedSpeciesProfile("Eclipta alba", "False Daisy", "Bhringraj", "broadleaf", "prostrate", "medium", 30.0, "Moisture-loving broadleaf weed with white flowers"),
            WeedSpeciesProfile("Commelina benghalensis", "Dayflower", "Kankawa", "broadleaf", "creeping", "high", 25.0, "Fleshy creeping weed producing aerial and subterranean seeds"),
            WeedSpeciesProfile("Cyperus iria", "Rice Flatsedge", "Motha / Moria", "sedge", "tufted", "high", 40.0, "Annual sedge with yellow-brown umbel inflorescence"),
            WeedSpeciesProfile("Cyperus difformis", "Smallflower Umbrella Sedge", "Gheewala Motha", "sedge", "tufted", "high", 35.0, "Dense globose heads in saturated lowlands"),
            WeedSpeciesProfile("Leptochloa chinensis", "Red Sprangletop", "Dhan ka Ghas", "grass", "erect", "high", 70.0, "Aggressive semi-aquatic grass weed"),
            WeedSpeciesProfile("Ammannia spp.", "Redstem", "Dadmari", "broadleaf", "erect", "medium", 25.0, "Aquatic and lowland marsh broadleaf weed"),
        ],
        target_crops=["Rice"],
    ),
    "wheat": IndianCropProfile(
        context_id="wheat",
        crop_name="Wheat",
        scientific_name="Triticum aestivum",
        season="rabi",
        soil_types=["Alluvial sandy loam", "Clay loam", "Cracked dry loam", "Stubble residue"],
        default_safety_buffer_cm=5.0,
        key_weeds=[
            WeedSpeciesProfile("Phalaris minor", "Canary Grass / Little Seed", "Gulli Danda", "grass", "erect", "critical", 50.0, "Severe mimic weed of wheat causing up to 60% yield loss"),
            WeedSpeciesProfile("Chenopodium album", "Lamb's Quarters", "Bathua", "broadleaf", "erect", "high", 40.0, "Ubiquitous rabi broadleaf weed with powdery whitish foliage"),
            WeedSpeciesProfile("Avena ludoviciana", "Wild Oat", "Jangli Jai", "grass", "erect", "critical", 75.0, "Aggressive tall competitor with dropping panicles"),
            WeedSpeciesProfile("Convolvulus arvensis", "Field Bindweed", "Hiran Khuri", "broadleaf", "creeping", "high", 20.0, "Deep-rooted perennial vine strangling wheat tillers"),
            WeedSpeciesProfile("Rumex dentatus", "Toothed Dock", "Jangli Palak", "broadleaf", "erect", "medium", 45.0, "Broadleaf rosette with serrated leaves in wet pockets"),
            WeedSpeciesProfile("Melilotus indica", "Sweet Clover", "Senji", "broadleaf", "erect", "medium", 35.0, "Leguminous annual rabi weed with small yellow flowers"),
        ],
        target_crops=["Wheat"],
    ),
    "mustard": IndianCropProfile(
        context_id="mustard",
        crop_name="Mustard & Rapeseed",
        scientific_name="Brassica juncea",
        season="rabi",
        soil_types=["Sandy loam", "Light loam", "Dry crust", "Cloddy soil"],
        default_safety_buffer_cm=6.0,
        key_weeds=[
            WeedSpeciesProfile("Chenopodium album", "Lamb's Quarters", "Bathua", "broadleaf", "erect", "high", 40.0, "Dominant broadleaf weed during early vegetative stage"),
            WeedSpeciesProfile("Asphodelus tenuifolius", "Wild Onion", "Piazzi", "broadleaf", "erect", "high", 30.0, "Slender tubular leaves competing heavily in sandy fields"),
            WeedSpeciesProfile("Convolvulus arvensis", "Field Bindweed", "Hiran Khuri", "broadleaf", "creeping", "high", 20.0, "Twining vine wrapping around mustard stems"),
            WeedSpeciesProfile("Anagallis arvensis", "Scarlet Pimpernel", "Krishnanil", "broadleaf", "prostrate", "medium", 15.0, "Low-growing broadleaf with blue/red flowers"),
            WeedSpeciesProfile("Orobanche aegyptiaca", "Broomrape", "Bhanghi", "broadleaf", "erect", "critical", 25.0, "Root parasite lacking chlorophyll that severely damages mustard"),
        ],
        target_crops=["Mustard", "Toria", "Raya"],
    ),
    "maize": IndianCropProfile(
        context_id="maize",
        crop_name="Maize (Corn)",
        scientific_name="Zea mays",
        season="kharif",
        soil_types=["Deep loam", "Red gravelly loam", "Ridge-and-furrow soil", "Crusted clay"],
        default_safety_buffer_cm=7.0,
        key_weeds=[
            WeedSpeciesProfile("Echinochloa colona", "Jungle Rice", "Shama", "grass", "erect", "critical", 45.0, "Widespread grass competitor in initial 30 days"),
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "critical", 30.0, "Extremely persistent tuberous sedge with dark green glossy leaves"),
            WeedSpeciesProfile("Ageratum conyzoides", "Billy Goat Weed", "Ajgandha", "broadleaf", "erect", "high", 40.0, "Hairy broadleaf weed with purplish-white flower clusters"),
            WeedSpeciesProfile("Digitaria sanguinalis", "Crabgrass", "Takri Ghas", "grass", "creeping", "high", 35.0, "Finger-branched grass rooting at lower nodes"),
        ],
        target_crops=["Maize"],
    ),
    "sugarcane": IndianCropProfile(
        context_id="sugarcane",
        crop_name="Sugarcane",
        scientific_name="Saccharum officinarum",
        season="perennial",
        soil_types=["Deep black clay", "Alluvial silt", "Heavy trash residue", "Cracked Vertisol"],
        default_safety_buffer_cm=8.0,
        key_weeds=[
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "critical", 30.0, "Primary sedge infesting sugarcane inter-rows"),
            WeedSpeciesProfile("Cynodon dactylon", "Bermuda Grass", "Doob Ghas", "grass", "creeping", "critical", 15.0, "Extensively creeping perennial stoloniferous mat"),
            WeedSpeciesProfile("Dactyloctenium aegyptium", "Crowfoot Grass", "Makra Ghas", "grass", "tufted", "high", 35.0, "Star-like digitate spikes competing in early ratoon"),
            WeedSpeciesProfile("Convolvulus arvensis", "Field Bindweed", "Hiran Khuri", "broadleaf", "creeping", "high", 20.0, "Climber covering trash and young sugarcane shoots"),
        ],
        target_crops=["Sugarcane"],
    ),
    "vegetables": IndianCropProfile(
        context_id="vegetables",
        crop_name="Vegetable Crops",
        scientific_name="Solanum lycopersicum / melongena / Allium cepa",
        season="kharif/rabi",
        soil_types=["Raised bed loam", "Mulched soil", "Drip-irrigated silt", "Organic residue"],
        default_safety_buffer_cm=5.0,
        key_weeds=[
            WeedSpeciesProfile("Amaranthus viridis", "Slender Amaranth", "Cholai", "broadleaf", "erect", "high", 45.0, "Rapidly growing broadleaf weed in vegetable beds"),
            WeedSpeciesProfile("Portulaca oleracea", "Purslane", "Kulfi / Noniya", "broadleaf", "prostrate", "high", 15.0, "Fleshy succulent broadleaf hugging soil surface"),
            WeedSpeciesProfile("Trianthema portulacastrum", "Horse Purslane", "Bishkhapra", "broadleaf", "prostrate", "critical", 20.0, "Aggressive early competitor covering bed surfaces"),
            WeedSpeciesProfile("Digera arvensis", "False Amaranth", "Lasanwa", "broadleaf", "erect", "medium", 35.0, "Annual herb with pinkish-white flowers"),
            WeedSpeciesProfile("Celosia argentea", "Silver Cockscomb", "Safed Murga", "broadleaf", "erect", "medium", 50.0, "Silvery-pink plumose spikes in warm vegetables"),
            WeedSpeciesProfile("Euphorbia hirta", "Asthma Plant", "Dudhi", "broadleaf", "prostrate", "medium", 20.0, "Milky latex herb in disturbed garden soils"),
            WeedSpeciesProfile("Acalypha indica", "Indian Nettle", "Kuppi", "broadleaf", "erect", "medium", 30.0, "Cat-attracting nettle weed in vegetable furrows"),
            WeedSpeciesProfile("Eclipta alba", "False Daisy", "Bhringraj", "broadleaf", "prostrate", "medium", 30.0, "Moist furrows and drip line borders"),
            WeedSpeciesProfile("Boerhaavia diffusa", "Spreading Hogweed", "Punarnava", "broadleaf", "prostrate", "high", 25.0, "Diffusely branched perennial tap-rooted herb"),
            WeedSpeciesProfile("Solanum nigrum", "Black Nightshade", "Makoi", "broadleaf", "erect", "high", 40.0, "Solanaceous weed sharing pests with tomato and brinjal"),
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "critical", 30.0, "Ubiquitous tuberous sedge piercing mulch"),
            WeedSpeciesProfile("Chenopodium album", "Lamb's Quarters", "Bathua", "broadleaf", "erect", "high", 40.0, "Winter vegetable beds (cabbage, cauliflower, onion)"),
        ],
        target_crops=["Tomato", "Brinjal", "Okra", "Onion", "Cabbage", "Cauliflower"],
    ),
    "sorghum_millets": IndianCropProfile(
        context_id="sorghum_millets",
        crop_name="Sorghum & Millets",
        scientific_name="Sorghum bicolor / Pennisetum glaucum",
        season="kharif",
        soil_types=["Red sandy soil", "Black shallow soil", "Cracked hardpan", "Stony gravel"],
        default_safety_buffer_cm=6.0,
        key_weeds=[
            WeedSpeciesProfile("Dactyloctenium aegyptium", "Crowfoot Grass", "Makra", "grass", "tufted", "high", 35.0, "Early drought-resistant grass in dryland millets"),
            WeedSpeciesProfile("Cynodon dactylon", "Bermuda Grass", "Doob", "grass", "creeping", "high", 15.0, "Forms dense runner mats across red sandy loam"),
            WeedSpeciesProfile("Panicum repens", "Torpedo Grass", "Bansi Ghas", "grass", "creeping", "high", 50.0, "Perennial rhizomatous grass tough to dislodge"),
            WeedSpeciesProfile("Perotis indica", "Indian Tail Grass", "Lomdi Ghas", "grass", "tufted", "medium", 30.0, "Coarse sandy soil indicator grass"),
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "critical", 30.0, "Deep root tubers surviving dry spells"),
            WeedSpeciesProfile("Fimbristylis miliacea", "Lesser Fringed Sedge", "Mori", "sedge", "tufted", "medium", 35.0, "Moist patches in millet fields"),
            WeedSpeciesProfile("Abutilon indicum", "Indian Mallow", "Kanghi", "broadleaf", "erect", "high", 65.0, "Stout velvety subshrub in rainfed tracts"),
            WeedSpeciesProfile("Achyranthes aspera", "Prickly Chaff Flower", "Chirchita / Latjira", "broadleaf", "erect", "high", 60.0, "Stiff hooked bracts adhering to rover wheels"),
            WeedSpeciesProfile("Aerva lanata", "Mountain Knotgrass", "Gorakhbuti", "broadleaf", "prostrate", "medium", 30.0, "Woolly white spikes in dry stony terrain"),
            WeedSpeciesProfile("Amaranthus spinosus", "Spiny Amaranth", "Kanta Cholai", "broadleaf", "erect", "critical", 55.0, "Sharp axial spines damaging tyres and belts"),
            WeedSpeciesProfile("Acanthospermum hispidum", "Starbur", "Kanti", "broadleaf", "erect", "high", 40.0, "Spiny star-shaped burs infesting millets"),
            WeedSpeciesProfile("Leucas aspera", "Common Leucas", "Goma", "broadleaf", "erect", "medium", 35.0, "Aromatic white-flowered labiate herb"),
        ],
        target_crops=["Sorghum (Jowar)", "Pearl Millet (Bajra)", "Finger Millet (Ragi)"],
    ),
    "pulses_oilseeds": IndianCropProfile(
        context_id="pulses_oilseeds",
        crop_name="Pulses & Oilseeds",
        scientific_name="Cicer arietinum / Cajanus cajan / Glycine max",
        season="kharif/rabi",
        soil_types=["Deep Vertisol", "Cracked black cotton soil", "Sandy gravel", "Dry clods"],
        default_safety_buffer_cm=6.5,
        key_weeds=[
            WeedSpeciesProfile("Abutilon indicum", "Indian Mallow", "Kanghi", "broadleaf", "erect", "high", 60.0, "Persistent competitor in chickpea and pigeonpea"),
            WeedSpeciesProfile("Achyranthes aspera", "Prickly Chaff", "Chirchita", "broadleaf", "erect", "high", 50.0, "Fast colonizer in rainfed pulses"),
            WeedSpeciesProfile("Aerva lanata", "Woolly Plant", "Gorakhganja", "broadleaf", "prostrate", "medium", 25.0, "Drought-hardy broadleaf in red and black soils"),
            WeedSpeciesProfile("Amaranthus spinosus", "Spiny Amaranth", "Kanta Cholai", "broadleaf", "erect", "critical", 55.0, "Vigorous competitor in soybean and groundnut"),
            WeedSpeciesProfile("Acanthospermum hispidum", "Starbur", "Bikhra", "broadleaf", "erect", "high", 40.0, "Thorny burrs spreading across oilseed rows"),
            WeedSpeciesProfile("Leucas aspera", "Leucas", "Dronapushpi", "broadleaf", "erect", "medium", 30.0, "Common annual in legume inter-rows"),
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "critical", 30.0, "Deep tubers infesting black cotton soils"),
        ],
        target_crops=["Chickpea (Gram)", "Pigeonpea (Arhar)", "Soybean", "Groundnut", "Mustard"],
    ),
    "cotton": IndianCropProfile(
        context_id="cotton",
        crop_name="Cotton",
        scientific_name="Gossypium hirsutum",
        season="kharif",
        soil_types=["Deep black cotton soil", "Vertisol cracks", "Cloddy clay", "Shadow furrows"],
        default_safety_buffer_cm=8.0,
        key_weeds=[
            WeedSpeciesProfile("Trianthema portulacastrum", "Horse Purslane", "Bishkhapra", "broadleaf", "prostrate", "critical", 20.0, "Dominant broadleaf weed during first 45 days"),
            WeedSpeciesProfile("Digera arvensis", "False Amaranth", "Lasanwa", "broadleaf", "erect", "high", 40.0, "Tall succulent weed shading young cotton plants"),
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "critical", 30.0, "Pervasive sedge forming root carpets"),
            WeedSpeciesProfile("Celosia argentea", "White Cockscomb", "Safed Murga", "broadleaf", "erect", "high", 60.0, "Vigorous competitor in black cotton soils"),
            WeedSpeciesProfile("Cynodon dactylon", "Bermuda Grass", "Doob", "grass", "creeping", "high", 15.0, "Tough creeping stolons between wide cotton rows"),
            WeedSpeciesProfile("Dactyloctenium aegyptium", "Crowfoot Grass", "Makra", "grass", "tufted", "high", 35.0, "Annual grass infesting warm wet cotton beds"),
        ],
        target_crops=["Cotton (Kapas)"],
    ),
    "orchard": IndianCropProfile(
        context_id="orchard",
        crop_name="Fruit Orchards",
        scientific_name="Mangifera indica / Psidium guajava / Malus domestica",
        season="perennial",
        soil_types=["Orchard floor loam", "Tree canopy shadow", "Stony soil", "Dry leaf litter"],
        default_safety_buffer_cm=10.0,
        key_weeds=[
            WeedSpeciesProfile("Cynodon dactylon", "Bermuda Grass", "Doob Ghas", "grass", "creeping", "high", 15.0, "Extensive turf carpeting orchard floor"),
            WeedSpeciesProfile("Cyperus rotundus", "Purple Nutsedge", "Motha", "sedge", "erect", "high", 30.0, "Clumping sedge in tree drip zones"),
            WeedSpeciesProfile("Parthenium hysterophorus", "Carrot Grass / Congress Grass", "Gajar Ghas", "broadleaf", "erect", "critical", 80.0, "Toxic invasive weed causing severe allelopathic suppression and contact dermatitis"),
            WeedSpeciesProfile("Bidens pilosa", "Beggar Ticks", "Chirchita", "broadleaf", "erect", "medium", 60.0, "Barbed achenes adhering to rover chassis"),
        ],
        target_crops=["Mango", "Guava", "Apple", "Citrus"],
    ),
}


def get_crop_profile(context_id: str) -> IndianCropProfile:
    """Returns the Indian crop profile for a given context ID, defaulting to wheat."""
    cid = context_id.lower().strip()
    return INDIAN_CROP_PROFILES.get(cid, INDIAN_CROP_PROFILES["wheat"])


def list_available_contexts() -> List[Dict[str, Any]]:
    """Returns clean summary list of available Indian crop contexts for UI selectors."""
    return [
        {
            "id": p.context_id,
            "name": p.crop_name,
            "scientific_name": p.scientific_name,
            "season": p.season,
            "safety_buffer_cm": p.default_safety_buffer_cm,
            "weed_count": len(p.key_weeds),
            "top_weeds": [w.scientific_name for w in p.key_weeds[:4]],
        }
        for p in INDIAN_CROP_PROFILES.values()
    ]


def match_weed_species(
    crop_context: str,
    bbox_aspect_ratio: float,
    area_norm: float,
) -> Optional[WeedSpeciesProfile]:
    """
    Selects the most probable Indian weed species candidate based on:
    - Current crop context
    - Morphological indicators: aspect ratio (slender/grass vs broad/creeping)
    - Relative canopy area
    """
    profile = get_crop_profile(crop_context)
    weeds = profile.key_weeds
    if not weeds:
        return None

    # Aspect ratio > 1.8 -> Slender grass / tall sedge
    # Aspect ratio < 1.3 with large area -> Broadleaf rosette / prostrate
    if bbox_aspect_ratio > 1.8:
        grasses = [w for w in weeds if w.weed_type in ("grass", "sedge")]
        return grasses[0] if grasses else weeds[0]
    else:
        broadleaves = [w for w in weeds if w.weed_type == "broadleaf"]
        return broadleaves[0] if broadleaves else weeds[0]
