"""
Disease care guidance reference (Phase 1 completion).

Static, curated reference for the 13 classes the trained classifier supports
(see models/disease_metrics.json / ml/datasets/plant_disease/manifest.csv).
This is general, well-established plant-pathology extension guidance (pathogen
identity, standard cultural/chemical control categories) — not a per-field
dosage prescription. It is intentionally generic on chemical control (control
class, not brand/rate) because exact product and dosage depends on local
regulations, crop stage and label instructions that this system cannot see.

Not a substitute for a local agricultural extension officer or a soil-test-
calibrated recommendation for anything consequential.
"""

from __future__ import annotations

CareGuidance = dict[str, object]

_GUIDANCE: dict[str, CareGuidance] = {
    "apple__apple_scab": {
        "pathogen_type": "fungal",
        "pathogen": "Venturia inaequalis",
        "severity": "MEDIUM",
        "recommended_actions": [
            "Remove and destroy fallen leaves and infected fruit to reduce overwintering spores.",
            "Prune to improve canopy airflow and sunlight penetration.",
            "Apply a labelled fungicide (e.g. a protectant like captan or a triazole) at green-tip through petal-fall per local label instructions.",
        ],
        "prevention": [
            "Choose scab-resistant apple varieties where replanting.",
            "Avoid overhead irrigation that keeps leaves wet for long periods.",
            "Rake and remove leaf litter each autumn.",
        ],
    },
    "apple__black_rot": {
        "pathogen_type": "fungal",
        "pathogen": "Botryosphaeria obtusa",
        "severity": "MEDIUM",
        "recommended_actions": [
            "Prune out cankered, dead, or mummified wood and fruit; this is the primary spore source.",
            "Remove and destroy fallen fruit and leaves promptly.",
            "Apply a labelled fungicide during the growing season if pressure is high, following local guidance.",
        ],
        "prevention": [
            "Maintain tree vigor — stressed/wounded trees are more susceptible.",
            "Avoid mechanical injury to bark and fruit.",
            "Sanitize pruning tools between trees.",
        ],
    },
    "apple__cedar_apple_rust": {
        "pathogen_type": "fungal",
        "pathogen": "Gymnosporangium juniperi-virginianae",
        "severity": "LOW",
        "recommended_actions": [
            "Remove nearby juniper/cedar hosts within a few hundred meters where feasible — the fungus alternates between apple and juniper.",
            "Apply a protectant fungicide from pink bud through several weeks after petal-fall in high-pressure areas.",
        ],
        "prevention": [
            "Plant rust-resistant apple cultivars.",
            "Avoid planting new apple trees near ornamental junipers/cedars.",
        ],
    },
    "apple__healthy": {
        "pathogen_type": None,
        "pathogen": None,
        "severity": "NONE",
        "recommended_actions": ["No disease detected — continue routine monitoring."],
        "prevention": [
            "Keep up regular scouting, balanced fertilization and proper pruning to maintain resistance.",
        ],
    },
    "grapes__black_rot": {
        "pathogen_type": "fungal",
        "pathogen": "Guignardia bidwellii",
        "severity": "HIGH",
        "recommended_actions": [
            "Remove mummified berries and infected canes during dormant pruning — they carry the pathogen over winter.",
            "Improve canopy airflow via shoot thinning and leaf removal around fruit clusters.",
            "Apply a labelled fungicide program from early shoot growth through berry set in high-pressure regions.",
        ],
        "prevention": [
            "Maintain an open canopy and good weed control to speed leaf drying.",
            "Remove wild/abandoned grapevines nearby that can harbor the fungus.",
        ],
    },
    "grapes__esca_black_measles": {
        "pathogen_type": "fungal (trunk-disease complex)",
        "pathogen": "Phaeomoniella/Phaeoacremonium spp. and wood-rot fungi",
        "severity": "HIGH",
        "recommended_actions": [
            "There is no curative chemical treatment once the trunk is infected — prune out and destroy dead/symptomatic wood well below visible discoloration.",
            "In severe cases, retrain the vine from a new trunk/sucker or replace the vine.",
            "Avoid pruning during wet weather, which favors infection through pruning wounds.",
        ],
        "prevention": [
            "Protect large pruning wounds with a wound sealant.",
            "Prune late in the dormant season when infection risk is lower.",
            "Source certified disease-free planting material.",
        ],
    },
    "grapes__healthy": {
        "pathogen_type": None,
        "pathogen": None,
        "severity": "NONE",
        "recommended_actions": ["No disease detected — continue routine monitoring."],
        "prevention": [
            "Maintain canopy management and a regular scouting schedule.",
        ],
    },
    "grapes__leaf_blight": {
        "pathogen_type": "fungal",
        "pathogen": "Pseudocercospora vitis (Isariopsis leaf spot)",
        "severity": "MEDIUM",
        "recommended_actions": [
            "Remove and destroy heavily infected leaves where practical.",
            "Improve canopy ventilation via leaf pulling and shoot positioning.",
            "Apply a labelled fungicide if pressure is building, per local guidance.",
        ],
        "prevention": [
            "Avoid overhead irrigation late in the day.",
            "Maintain balanced nitrogen — excess vegetative growth increases humidity in the canopy.",
        ],
    },
    "maize__common_rust": {
        "pathogen_type": "fungal",
        "pathogen": "Puccinia sorghi",
        "severity": "LOW",
        "recommended_actions": [
            "Most modern hybrids tolerate common rust well — a fungicide is rarely justified unless pressure is severe and the crop is young.",
            "If treating, apply a labelled foliar fungicide at first sign of pustules on upper leaves.",
        ],
        "prevention": [
            "Plant rust-resistant hybrids where available.",
            "Avoid very early planting in regions with high early-season rust pressure.",
        ],
    },
    "maize__gray_leaf_spot": {
        "pathogen_type": "fungal",
        "pathogen": "Cercospora zeae-maydis",
        "severity": "MEDIUM",
        "recommended_actions": [
            "Rotate away from maize for at least one season where the field has heavy crop residue and prior infection.",
            "Apply a labelled foliar fungicide at tasseling if disease is present on leaves below the ear at that stage.",
        ],
        "prevention": [
            "Use tillage to bury infected residue, or rotate crops — the fungus survives on maize debris.",
            "Choose hybrids with better gray leaf spot tolerance in high-risk fields.",
        ],
    },
    "maize__healthy": {
        "pathogen_type": None,
        "pathogen": None,
        "severity": "NONE",
        "recommended_actions": ["No disease detected — continue routine monitoring."],
        "prevention": [
            "Maintain crop rotation and residue management as a standing precaution.",
        ],
    },
    "maize__northern_leaf_blight": {
        "pathogen_type": "fungal",
        "pathogen": "Exserohilum turcicum",
        "severity": "MEDIUM",
        "recommended_actions": [
            "Scout regularly from tasseling onward; a fungicide application is most valuable if lesions appear on the ear leaf or above before/at tasseling.",
            "Rotate out of maize or till residue where the field has a history of heavy infection.",
        ],
        "prevention": [
            "Choose hybrids with northern leaf blight resistance genes in high-risk areas.",
            "Rotate crops to reduce residue-borne inoculum.",
        ],
    },
    "orange__citrus_greening_hlb": {
        "pathogen_type": "bacterial (insect-vectored, incurable)",
        "pathogen": "Candidatus Liberibacter spp. (Huanglongbing), spread by the Asian citrus psyllid",
        "severity": "HIGH",
        "recommended_actions": [
            "There is no cure — infected trees do not recover. Report suspected cases to local agricultural authorities, as HLB is often a regulated/notifiable disease.",
            "Remove and destroy confirmed infected trees promptly to reduce the source of psyllid-transmitted spread to healthy trees.",
            "Control the Asian citrus psyllid vector with a locally-recommended insecticide program on remaining healthy trees.",
        ],
        "prevention": [
            "Source certified disease-free nursery stock only.",
            "Monitor and control psyllid populations proactively, especially on new flush growth.",
            "Coordinate area-wide vector management with neighboring growers — HLB spreads faster where control is patchy.",
        ],
    },
}

_DEFAULT_GUIDANCE: CareGuidance = {
    "pathogen_type": None,
    "pathogen": None,
    "severity": "UNKNOWN",
    "recommended_actions": [
        "This condition doesn't have curated guidance yet — consult a local agricultural extension office before acting.",
    ],
    "prevention": [],
}


def get_care_guidance(label: str) -> CareGuidance:
    """label is the 'crop__condition_slug' key used throughout the disease pipeline."""
    return dict(_GUIDANCE.get(label, _DEFAULT_GUIDANCE))
