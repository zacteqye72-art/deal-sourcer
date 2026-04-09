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
]


def is_pet_related(listing: Listing) -> bool:
    """Check if a listing is related to pet businesses/apps."""
    text = f"{listing.title or ''} {listing.description or ''}".lower()
    return any(kw in text for kw in PET_KEYWORDS)
