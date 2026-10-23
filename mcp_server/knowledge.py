"""Deterministic veterinary safety knowledge for Dr. Paws.

Rules here run before any LLM call, so a known emergency can never be
downgraded by a model. Sources: ASPCA Animal Poison Control and AVMA
pet first-aid guidance (general owner-level advice, not a diagnosis).
"""

URGENCY_ORDER = {"HOME_CARE": 0, "VISIT_SOON": 1, "EMERGENCY": 2}

# Symptom keywords that always mean "go to an emergency vet now".
RED_FLAGS = {
    "not breathing": "Breathing has stopped or is severely impaired.",
    "difficulty breathing": "Breathing difficulty can become fatal within minutes.",
    "struggling to breathe": "Breathing difficulty can become fatal within minutes.",
    "choking": "Airway obstruction needs immediate help.",
    "seizure": "Seizures can signal poisoning or neurological emergencies.",
    "collapsed": "Collapse can indicate shock, heart or internal bleeding problems.",
    "unconscious": "Loss of consciousness is always an emergency.",
    "bloated": "A swollen, hard belly in dogs can be bloat (GDV), which is fatal without surgery.",
    "swollen belly": "A swollen, hard belly in dogs can be bloat (GDV), which is fatal without surgery.",
    "retching": "Unproductive retching can be bloat (GDV).",
    "hit by a car": "Trauma causes internal injuries that are not visible.",
    "heavy bleeding": "Uncontrolled bleeding needs immediate care.",
    "pale gums": "Pale or white gums suggest shock or blood loss.",
    "blue gums": "Blue gums mean the pet is not getting enough oxygen.",
    "can't urinate": "A blocked bladder (common in male cats) is fatal within 24-72 hours.",
    "cannot urinate": "A blocked bladder (common in male cats) is fatal within 24-72 hours.",
    "straining to pee": "A blocked bladder (common in male cats) is fatal within 24-72 hours.",
    "heatstroke": "Heatstroke damages organs quickly.",
    "snake bite": "Venom acts fast; antivenom must be given early.",
}

VISIT_SOON_FLAGS = {
    "vomiting": "Repeated vomiting can cause dehydration.",
    "diarrhea": "Diarrhea lasting more than a day can cause dehydration.",
    "not eating": "Loss of appetite for over 24 hours needs a check-up (12 hours for cats).",
    "limping": "Limping can mean a sprain, fracture or joint problem.",
    "lethargic": "Unusual tiredness often signals an underlying illness.",
    "scratching": "Persistent itching often means allergies, mites or infection.",
    "ear": "Ear problems are usually infections that need medication.",
    "eye": "Eye problems can worsen quickly and threaten sight.",
}

# food -> species -> (severity, why, action)
TOXIC_FOODS = {
    "chocolate": {
        "dog": ("HIGH", "Contains theobromine and caffeine, which dogs cannot clear; dark and baking chocolate are the most dangerous.",
                "Call a vet or animal poison line now. Note the type and amount eaten and your dog's weight. Do not induce vomiting unless a vet tells you to."),
        "cat": ("HIGH", "Contains theobromine and caffeine, which are toxic to cats.",
                "Call a vet now with the type and amount eaten."),
    },
    "grapes": {
        "dog": ("HIGH", "Grapes and raisins can cause sudden kidney failure in dogs, even in small amounts.",
                "Go to a vet immediately. Early decontamination is critical."),
        "cat": ("MEDIUM", "Grapes and raisins may cause kidney damage in cats.",
                "Call a vet for advice."),
    },
    "raisins": "grapes",
    "xylitol": {
        "dog": ("HIGH", "Xylitol (in sugar-free gum, candy, some peanut butter) causes a rapid blood sugar crash and liver failure in dogs.",
                "Go to an emergency vet immediately, even if your dog seems fine."),
        "cat": ("MEDIUM", "Xylitol's effect on cats is less clear but it is not safe.",
                "Call a vet for advice."),
    },
    "onion": {
        "dog": ("HIGH", "Onions damage red blood cells and can cause anemia; cooked and powdered forms count.",
                "Call a vet, especially if a large amount was eaten."),
        "cat": ("HIGH", "Cats are even more sensitive than dogs to onion toxicity.",
                "Call a vet now."),
    },
    "garlic": "onion",
    "lily": {
        "cat": ("HIGH", "All parts of true lilies, even pollen or vase water, cause kidney failure in cats.",
                "Go to an emergency vet immediately. Treatment within 18 hours is critical."),
        "dog": ("LOW", "Lilies usually cause only mild stomach upset in dogs.",
                "Watch for vomiting; call a vet if it persists."),
    },
    "avocado": {
        "dog": ("LOW", "The flesh is low risk for dogs, but the pit can cause a blockage.",
                "If the pit was swallowed, call a vet."),
        "cat": ("LOW", "Low risk for cats; can cause stomach upset.",
                "Watch for vomiting or diarrhea."),
        "bird": ("HIGH", "Avocado contains persin, which is often fatal to birds.",
                 "Go to an avian vet immediately."),
    },
    "alcohol": {
        "dog": ("HIGH", "Alcohol causes dangerous drops in blood sugar, blood pressure and body temperature.",
                "Call a vet now."),
        "cat": ("HIGH", "Alcohol is dangerous for cats even in small amounts.",
                "Call a vet now."),
    },
    "paracetamol": {
        "cat": ("HIGH", "Paracetamol (acetaminophen) is deadly to cats; a single tablet can kill.",
                "Go to an emergency vet immediately."),
        "dog": ("HIGH", "Paracetamol can cause liver damage in dogs.",
                "Call a vet now with the dose taken."),
    },
    "acetaminophen": "paracetamol",
    "ibuprofen": {
        "dog": ("HIGH", "Ibuprofen causes stomach ulcers and kidney failure in dogs.",
                "Call a vet now with the dose taken."),
        "cat": ("HIGH", "Ibuprofen is highly toxic to cats.",
                "Call a vet now."),
    },
    "macadamia": {
        "dog": ("MEDIUM", "Macadamia nuts cause weakness, tremors and fever in dogs.",
                "Call a vet; symptoms usually appear within 12 hours."),
    },
    "coffee": "chocolate",
}

SAFE_TREATS = {
    "dog": "plain cooked chicken, carrots, apple slices without seeds, or plain pumpkin",
    "cat": "small pieces of plain cooked chicken or fish",
}


def lookup_food(food: str, species: str):
    """Return (severity, why, action) or None if unknown."""
    key = food.lower().strip()
    match = None
    for name in TOXIC_FOODS:
        if name in key or key in name:
            match = name
            break
    if not match:
        return None
    entry = TOXIC_FOODS[match]
    if isinstance(entry, str):  # alias
        entry = TOXIC_FOODS[entry]
    sp = species.lower().strip()
    if sp in entry:
        return entry[sp]
    # unknown species: use the most cautious entry
    return max(entry.values(), key=lambda v: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[v[0]])


def rule_triage(symptoms: str):
    """Return (urgency, reasons) from keyword rules."""
    text = symptoms.lower()
    reasons = [why for kw, why in RED_FLAGS.items() if kw in text]
    if reasons:
        return "EMERGENCY", sorted(set(reasons))
    reasons = [why for kw, why in VISIT_SOON_FLAGS.items() if kw in text]
    if reasons:
        return "VISIT_SOON", sorted(set(reasons))
    return "HOME_CARE", []
