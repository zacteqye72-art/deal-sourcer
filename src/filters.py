from src.models import Listing

PET_KEYWORDS = [
    "pet", "pets", "dog", "dogs", "cat", "cats", "puppy", "puppies",
    "kitten", "kittens", "veterinary", "vet ", "vets", "animal", "animals",
    "grooming", "pet care", "pet food", "pet shop", "pet store",
    "pet supply", "pet supplies", "pet sitter", "pet sitting",
    "dog walking", "pet adoption", "pet insurance", "pet health",
    "pet tracker", "pet app", "dog breed", "cat breed",
    "pet training", "dog training", "pet marketplace",
    "宠物",
    # pet wellness overlap
    "pet supplement", "pet vitamin", "pet cbd", "pet hemp",
    "dog supplement", "cat supplement", "pet probiotic",
    "pet treat", "dog treat", "cat treat", "raw pet food",
    "organic pet", "pet diet", "pet anxiety", "pet dental",
    "rabbit", "hamster", "bird", "fish tank", "aquarium",
    "reptile", "ferret", "livestock", "farm animal",
]

WELLNESS_KEYWORDS = [
    "wellness", "well-being", "wellbeing",
    "supplement", "supplements", "nutraceutical",
    "cbd", "hemp", "thc",
    "meditation", "mindfulness",
    "nutrition platform", "nutritional subscription",
    "holistic health", "natural health",
    "mental wellness", "mental health app",
    "sleep tracker", "sleep app",
    "anxiety relief", "stress relief",
    "probiotic", "prebiotic", "gut health",
    "vitamin subscription", "mineral supplement",
    "fitness tracker", "health tracker",
    "telehealth", "telemedicine",
    "health coaching", "wellness coaching",
    "yoga app", "meditation app",
    "健康",
]

PET_WELLNESS_KEYWORDS = PET_KEYWORDS + WELLNESS_KEYWORDS


def is_pet_related(listing: Listing) -> bool:
    """Check if a listing is related to pet or wellness businesses/apps."""
    text = f"{listing.title or ''} {listing.description or ''}".lower()
    return any(kw in text for kw in PET_WELLNESS_KEYWORDS)
