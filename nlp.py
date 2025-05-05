import re
import spacy
import json

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Direction and corner mappings
DIRECTION_MAP = {
    "left":     "WEST",
    "right":    "EAST",
    "front":    "NORTH",
    "back":     "SOUTH",
    "north":    "NORTH",
    "south":    "SOUTH",
    "east":     "EAST",
    "west":     "WEST",
    "forward":  "NORTH",
    "backward": "SOUTH"
}

CORNER_MAP = {
    "top left": "NW", "upper left": "NW",
    "top right": "NE", "upper right": "NE",
    "bottom left": "SW", "lower left": "SW",
    "bottom right": "SE", "lower right": "SE",
    "NE": "NE","SE": "SE","NW": "NW","SW": "SW",
    "ne": "NE","se": "SE","nw": "NW","sw": "SW"
}

# Directional words to exclude from noun extraction
DIRECTIONAL_WORDS = {
    "center", "left", "right", "top", "bottom",
    "front", "back", "north", "south", "east", "west",
    "upper", "lower", "forward", "backward"
}

def load_scene_state(file_path="scene_state.json"):
    """Load the scene state from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Scene state file '{file_path}' not found. Creating new scene.")
        return {"room": {"width": 5.0, "depth": 5.0, "height": 3.0}, "objects": []}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in scene state file '{file_path}'.")
        return {"room": {"width": 5.0, "depth": 5.0, "height": 3.0}, "objects": []}

# Global scene state
scene_state = load_scene_state()

def extract_numbers(text: str):
    return [float(m.group()) for m in re.finditer(r"\d+(\.\d+)?", text)]

def match_object_in_scene(ref_text):
    """
    Match a reference text to an object in the scene state.
    Returns the exact object description if found, or None if not found.
    """
    if not ref_text or "objects" not in scene_state:
        return None
    
    clean_ref = ref_text.lower().strip()
    for article in ["the ", "a ", "an "]:
        if clean_ref.startswith(article):
            clean_ref = clean_ref[len(article):]
    
    for obj in scene_state["objects"]:
        if clean_ref == obj["description"].lower():
            return obj["description"]
    
    for obj in scene_state["objects"]:
        if clean_ref in obj["description"].lower() or obj["description"].lower() in clean_ref:
            return obj["description"]
    
    if " " in clean_ref:
        for obj in scene_state["objects"]:
            obj_parts = obj["description"].lower().split()
            ref_parts = clean_ref.split()
            if any(part in obj_parts for part in ref_parts):
                return obj["description"]
    
    return None

def extract_object_reference(doc, deps=None):
    """
    Extract object references from NLP doc.
    Returns the object name (matched or first potential reference).
    """
    if deps is None:
        deps = ["dobj", "obj"]
    
    potential_refs = []
    
    for chunk in doc.noun_chunks:
        if chunk.root.dep_ in deps and chunk.root.text.lower() not in DIRECTIONAL_WORDS:
            clean_text = chunk.text.strip()
            for article in ["the ", "a ", "an "]:
                if clean_text.lower().startswith(article):
                    clean_text = clean_text[len(article):]
            potential_refs.append(clean_text)
    
    if not potential_refs:
        for token in doc:
            if token.dep_ in deps and token.pos_ in ("NOUN", "PROPN") and token.text.lower() not in DIRECTIONAL_WORDS:
                potential_refs.append(token.text)
    
    for ref in potential_refs:
        matched_obj = match_object_in_scene(ref)
        if matched_obj:
            return matched_obj
    
    return potential_refs[0] if potential_refs else None

def set_room(text: str) -> str:
    nums = extract_numbers(text)
    width, depth, height = (nums + [None, None, None])[:3]
    return f"set_room({width}, {depth}, {height})"

def create_object(text: str) -> str:
    text_l = text.lower().strip()
    doc    = nlp(text_l)

    # Default
    desc = None
    qty  = 1
    dims_source = text_l

    # 1) EXACT “create chair 4” (with optional “that are …” afterwards)
    m2 = re.match(r"^create\s+([a-z]+)\s+(\d+)(?:\s+that\s+are\b)?", text_l)
    if m2:
        noun, num_str = m2.group(1), m2.group(2)
        desc = f"{noun}_{num_str}"
        # Leave qty = 1
        # Strip off the matched part so dims extraction ignores that “4”
        dims_source = text_l[m2.end():].strip()

    else:
        # 2) “create 3 chairs …”
        m1 = re.match(r"^create\s+(\d+)\s+([a-z]+?)(?:s)?\b", text_l)
        if m1:
            qty = int(m1.group(1))
            noun = m1.group(2)
            desc = noun
            dims_source = text_l[m1.end():].strip()

    # 3) Fallback: first non‑directional noun chunk
    if not desc:
        for chunk in doc.noun_chunks:
            if (chunk.root.pos_ in ("NOUN","PROPN") 
               and chunk.root.text.lower() not in DIRECTIONAL_WORDS):
                cleaned = chunk.text.strip()
                for art in ("the ","a ","an "):
                    if cleaned.startswith(art):
                        cleaned = cleaned[len(art):]
                desc = re.sub(r"\s*\d+$", "", cleaned)  # drop trailing numbers
                break

    if not desc:
        # Last resort: any noun token
        desc = next(
            (tok.text for tok in doc 
             if tok.pos_ in ("NOUN","PROPN") 
             and tok.text.lower() not in DIRECTIONAL_WORDS),
            "object"
        )

    # 4) Extract dimensions from the remainder
    nums = extract_numbers(dims_source)
    # For the qty‑first pattern, we already removed the qty itself from dims_source
    w, d, h = (nums + [None, None, None])[:3]

    return f"create_object('{desc}', {w}, {d}, {h}, '{qty}')"




def place_relative(text: str) -> str:
    doc = nlp(text)
    
    target = extract_object_reference(doc, ["dobj", "obj"])
    ref = extract_object_reference(doc, ["pobj"])
    
    direction = next((DIRECTION_MAP.get(tok.text.lower()) for tok in doc if tok.text.lower() in DIRECTION_MAP), None)
    dist = extract_numbers(text)[0] if extract_numbers(text) else None
    
    return f"place_relative('{target}', '{ref}', '{direction}', {dist}, 0, 0)"

def align_object(text: str) -> str:
    doc = nlp(text)
    
    target = extract_object_reference(doc, ["dobj", "obj"])
    ref_name = extract_object_reference(doc, ["pobj"])
    
    mode_match = re.search(r"align .*? (?:to|with) the (\w+)", text.lower())
    mode = mode_match.group(1) if mode_match else None
    
    anchors = [tok.text for tok in doc if tok.text.lower() in ("center", "left", "right", "top", "bottom")]
    target_anchor = anchors[0] if anchors else None
    ref_anchor = anchors[1] if len(anchors) > 1 else None
    
    offset = float(re.search(r"offset (\d+(\.\d+)?)", text.lower()).group(1)) if re.search(r"offset (\d+(\.\d+)?)", text.lower()) else 0.2
    direction = next((DIRECTION_MAP.get(tok.text.lower()) for tok in doc if tok.text.lower() in DIRECTION_MAP), None)
    
    return f"align_object('{target}', '{mode}', '{target_anchor}', '{ref_name}', '{ref_anchor}', {offset}, {repr(direction)})"

def place_on_top(text: str) -> str:
    doc = nlp(text)

    # 1) Get the “thing to place” via dobj/obj → lemma
    top_tok = next(
        (tok for tok in doc if tok.dep_ in ("dobj", "obj") and tok.pos_ == "NOUN"),
        None
    )
    top = top_tok.lemma_ if top_tok else "object"

    # 2) Get the “thing to place onto” via the INNER preposition “of”
    bottom_tok = next(
        (tok for tok in doc if tok.dep_ == "pobj" and tok.head.lemma_ == "of"),
        None
    )
    if bottom_tok:
        # build just the compound phrase (e.g. "coffee table")
        compounds = [child.text for child in bottom_tok.lefts
                     if child.dep_ in ("compound", "amod")]
        bottom = " ".join(compounds + [bottom_tok.text])
    else:
        # fallback to first pobj’s full subtree
        fallback = next((tok for tok in doc if tok.dep_ == "pobj"), None)
        bottom = " ".join(w.text for w in fallback.subtree) if fallback else "object"

    return f"place_on_top('{top}', '{bottom}', 0, 0, 0)"



def mount_on_wall(text: str) -> str:
    doc = nlp(text)
    
    obj = extract_object_reference(doc, ["dobj", "obj"])
    
    wall = next((DIRECTION_MAP[tok.text.lower()] for tok in doc if tok.text.lower() in DIRECTION_MAP), None)
    nums = extract_numbers(text)
    dist = nums[0] if nums else 0.05
    pos = nums[1] if len(nums) > 1 else 0.5
    height = nums[2] if len(nums) > 2 else None
    
    return f"mount_on_wall('{obj}', '{wall}', {dist}, {pos}, {height})"



def move_object(text: str) -> str:
    doc = nlp(text.lower())

    # 1) Extract the object as full noun phrase (compounds + head)
    obj_tok = next(
        (tok for tok in doc if tok.dep_ in ("dobj", "obj") and tok.pos_ == "NOUN"),
        None
    )
    if obj_tok:
        compounds = [c.text for c in obj_tok.lefts if c.dep_ in ("compound", "amod")]
        obj = " ".join(compounds + [obj_tok.text])
    else:
        obj = "object"

    # 2) Find the first directional word in the full map
    dir_tok = next((tok.text for tok in doc if tok.text in DIRECTION_MAP), None)
    direction = DIRECTION_MAP.get(dir_tok) if dir_tok else None

    # 3) First numeric token = distance
    nums = extract_numbers(text)
    dist = nums[0] if nums else None

    return f"move_object('{obj}', '{direction}', {dist})"


def rotate_object(text: str) -> str:
    doc = nlp(text)
    
    obj = extract_object_reference(doc, ["dobj", "obj"])
    
    turns = int(extract_numbers(text)[0] if extract_numbers(text) else 1)
    
    return f"rotate_object('{obj}', {turns})"

def place_in_room_corner(text: str) -> str:
    doc = nlp(text.lower())
    
    # Extract object reference
    obj = extract_object_reference(doc, ["dobj", "obj"])
    
    # Create regex pattern for all corner keywords (case-insensitive)
    corner_keywords = '|'.join([re.escape(phrase) for phrase in CORNER_MAP.keys()])
    corner_pattern = rf'\b({corner_keywords})\b'
    
    # Find the first matching corner keyword in the text
    corner_match = re.search(corner_pattern, text.lower())
    corner = CORNER_MAP.get(corner_match.group(1)) if corner_match else None
    
    # Extract numbers for wall distance and fallback
    nums = extract_numbers(text)
    wall_dist = nums[0] if nums else 0.2
    
    # Extract facing direction
    facing = next((DIRECTION_MAP.get(tok.text.lower()) for tok in doc if tok.text.lower() in DIRECTION_MAP), None)
    
    # Generate DSL command
    return f"place_in_room_corner('{obj}', '{corner}', {wall_dist}, '{facing}')"

def place_along_wall(text: str) -> str:
    doc = nlp(text)
    
    obj = extract_object_reference(doc, ["dobj", "obj"])
    
    wall = next((DIRECTION_MAP.get(tok.text.lower()) for tok in doc if tok.text.lower() in DIRECTION_MAP), None)
    nums = extract_numbers(text)
    pos = nums[0] if nums else 0.5
    dist = nums[1] if len(nums) > 1 else 0.2
    
    return f"place_along_wall('{obj}', '{wall}', {pos}, {dist})"

def arrange_in_group(text: str) -> str:
    doc = nlp(text)
    
    objs = []
    for chunk in doc.noun_chunks:
        if 'in a' not in chunk.text.lower():
            clean_text = chunk.text.strip()
            for article in ["the ", "a ", "an "]:
                if clean_text.lower().startswith(article):
                    clean_text = clean_text[len(article):]
            if clean_text.lower() != "circle" and chunk.root.text.lower() not in DIRECTIONAL_WORDS:
                objs.append(clean_text)
    
    formation_match = re.search(r"in a (\w+)", text.lower())
    formation = formation_match.group(1) if formation_match else "circle"
    nums = extract_numbers(text)
    spacing = nums[0] if nums else 0.5
    
    return f"arrange_in_group({objs!r}, '{formation}', None, None, {spacing}, 'inward')"

def place_relative_multi(text: str) -> str:
    """
    Generate DSL for placing an object relative to multiple reference objects.
    Examples:
    - "Place a lamp between a sofa and a table" -> place_relative_multi('lamp', ['sofa', 'table'], [None, None], [1.0, 1.0])
    - "Position a lamp 0.3m west of a bed and 0.4m to the south of a nightstand" ->
      place_relative_multi('lamp', ['bed', 'nightstand'], ['WEST', 'SOUTH'], [0.3, 0.4])
    """
    text_l = text.lower().strip()
    doc = nlp(text)

    # 1) Identify target object (last noun before directional phrases)
    target = "object"
    for tok in reversed(doc):
        if tok.pos_ in ("NOUN", "PROPN"):
            # Rebuild noun phrase: compounds + head noun
            compounds = [t.text for t in doc if t.dep_ == "compound" and t.head == tok]
            target = " ".join(compounds + [tok.lemma_])
            break

    # 2) Parse reference objects, directions, and distances
    refs = []
    dirs = []
    distances = extract_numbers(text_l)
    
    # Look for patterns like "X west of Y" or "X to the south of Y"
    ref_pattern = r'(\d+\.\d+m?)\s+(west|east|north|south|to the\s+(west|east|north|south))\s+of\s+a\s+([\w\s]+?)(?:and|$)'
    matches = list(re.finditer(ref_pattern, text_l))
    
    for match in matches:
        distance, dir_full, dir_inner, ref_text = match.groups()
        # Clean direction
        direction = dir_inner if dir_inner else dir_full
        direction = direction.upper()
        # Clean reference object
        doc_ref = nlp(ref_text.strip())
        compounds = [t.text for t in doc_ref if t.dep_ == "compound"]
        head = next((t for t in doc_ref if t.pos_ in ("NOUN", "PROPN")), None)
        if head:
            ref_name = " ".join(compounds + [head.text])
            refs.append(ref_name)
            dirs.append(direction)
    
    # 3) Fallback: If no matches, try "between" pattern
    if not refs and "between" in text_l:
        before, after = text_l.split("between", 1)
        refs_text = after.split(",", 1)[0]
        parts = [p.strip() for p in re.split(r"\band\b", refs_text)]
        
        for part in parts:
            doc_ref = nlp(part)
            compounds = [tok.text for tok in doc_ref if tok.dep_ == "compound"]
            head = next((tok for tok in doc_ref if tok.pos_ in ("NOUN", "PROPN")), None)
            if head:
                name = " ".join(compounds + [head.text])
                refs.append(name)
        
        # Broadcast single distance if only one found
        if len(distances) == 1:
            distances = distances * len(refs)
        else:
            distances = distances[:len(refs)]
        dirs = [None] * len(refs)
    
    # 4) Validate and format output
    if not refs:
        return "Error: No reference objects identified"
    
    if len(distances) < len(refs):
        distances = distances + [1.0] * (len(refs) - len(distances))  # Default to 1.0
    elif len(distances) > len(refs):
        distances = distances[:len(refs)]
    
    if len(dirs) < len(refs):
        dirs = dirs + [None] * (len(refs) - len(dirs))
    
    return f"place_relative_multi('{target}', {refs}, {dirs}, {distances})"
