import math
import json

scene = {"objects": [], "constraints": [], "room_width": None, "room_depth": None, "room_height": None}

class SceneObject:
    def __init__(self, description, width, depth, height):
        self.description = description
        self.width = width
        self.depth = depth
        self.height = height
        self.x = None
        self.y = None
        self.z = None
        self.rotation = 0
        self.facing = "NORTH"
        self.bbox = None

    def __str__(self):
        if self.x is None or self.y is None or self.z is None:
            return f"{self.description} (unplaced)"
        return f"{self.description} at ({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

class Constraint:
    def __init__(self, type, details):
        self.type = type
        self.details = details

def calculate_position_and_bbox(obj, x, y, z):
    obj.x, obj.y, obj.z = x, y, z
    half_width = float(obj.width) / 2
    half_depth = float(obj.depth) / 2
    half_height = float(obj.height) / 2
    obj.bbox = {
        "x": [x - half_width, x + half_width],
        "y": [y - half_depth, y + half_depth],
        "z": [z - half_height, z + half_height]
    }
    print(f"[Debug] Placed {obj.description} at ({x:.2f}, {y:.2f}, {z:.2f})")
    print(f"[Debug] BBox: x={obj.bbox['x']}, y={obj.bbox['y']}")

def check_overlap_with_existing(target):
    for obj in scene["objects"]:
        if obj == target or obj.x is None:
            continue
        if (target.bbox["x"][1] > obj.bbox["x"][0] and target.bbox["x"][0] < obj.bbox["x"][1] and
            target.bbox["y"][1] > obj.bbox["y"][0] and target.bbox["y"][0] < obj.bbox["y"][1]):
            return True, obj.description
    return False, None

def within_room_boundaries(obj):
    if not all([scene["room_width"], scene["room_depth"], scene["room_height"]]):
        return True
    return (obj.bbox["x"][0] >= 0 and obj.bbox["x"][1] <= scene["room_width"] and
            obj.bbox["y"][0] >= 0 and obj.bbox["y"][1] <= scene["room_depth"] and
            obj.bbox["z"][0] >= 0 and obj.bbox["z"][1] <= scene["room_height"])

def save_scene():
    if not all([scene["room_width"], scene["room_depth"], scene["room_height"]]):
        print("[Warning] Cannot save scene: Room dimensions incomplete")
        return
    scene_data = {
        "room": {
            "width": scene["room_width"],
            "depth": scene["room_depth"],
            "height": scene["room_height"]
        },
        "objects": [
            {
                "description": obj.description,
                "width": obj.width,
                "depth": obj.depth,
                "height": obj.height,
                "x": obj.x,
                "y": obj.y,
                "z": obj.z,
                "rotation": obj.rotation,
                "facing": obj.facing
            } for obj in scene["objects"] if obj.x is not None
        ],
        "constraints": [vars(constraint) for constraint in scene["constraints"]]
    }
    with open("scene_state.json", "w") as f:
        json.dump(scene_data, f, indent=4)
    print("[DSL] Scene saved to scene_state.json")

def set_room(width, depth, height):
    scene["room_width"] = width
    scene["room_depth"] = depth
    scene["room_height"] = height
    print(f"[DSL] Room set to {width}x{depth}x{height}")
    save_scene()

def create_object(description, width, depth, height, x=None, y=None, z=None, quantity=1):
    """Creates one or more objects with unique descriptions, appending numeric suffixes if needed."""
    created_objects = []
    
    # Get existing descriptions to check for duplicates
    existing_descs = [obj.description.lower() for obj in scene["objects"]]
    
    for i in range(quantity):
        # Start with the base description
        base_desc = description
        new_desc = base_desc
        suffix = 0
        
        # For single object or first of multiple, try base description
        if i > 0 or quantity == 1:
            # Find next available suffix if needed
            while new_desc.lower() in existing_descs:
                new_desc = f"{base_desc}{suffix}"
                suffix += 1
        
        # Create new object with unique description
        obj = SceneObject(new_desc, width, depth, height)
        scene["objects"].append(obj)
        existing_descs.append(new_desc.lower())  # Update to avoid future conflicts
        
        # Place object if coordinates provided
        if x is not None and y is not None:
            z = z if z is not None else height / 2
            calculate_position_and_bbox(obj, x, y, z)
            overlaps, overlapping_obj = check_overlap_with_existing(obj)
            if overlaps:
                print(f"[Warning] {new_desc} overlaps with {overlapping_obj} - adjust manually")
            elif not within_room_boundaries(obj):
                print(f"[Warning] {new_desc} out of room bounds - adjust manually")
            else:
                print(f"[DSL] Created and placed {new_desc} at ({x:.2f}, {y:.2f}, {z:.2f})")
            save_scene()
        else:
            print(f"[DSL] Created {new_desc} (unplaced)")
        
        created_objects.append(obj)
    
    # Return single object if quantity=1, else list of objects
    return created_objects[0] if quantity == 1 else created_objects

def place_relative(target_desc, ref_desc, direction, distance = 0, offset_x=0, offset_y=0):
    target = next((obj for obj in scene["objects"] if obj.description == target_desc), None)
    ref = next((obj for obj in scene["objects"] if obj.description == ref_desc), None)
    if not target or not ref:
        print(f"[Error] Object {target_desc} or {ref_desc} not found")
        return
    if ref.x is None or ref.y is None:
        print(f"[Error] Reference {ref_desc} must be placed first")
        return

    # Store original coordinates in case we need to revert
    original_x, original_y, original_z = target.x, target.y, target.z
    original_bbox = target.bbox.copy() if hasattr(target, 'bbox') and target.bbox else None

    print(f"[Debug] Placing {target_desc} {direction} of {ref_desc} with distance={distance}, offset_x={offset_x}, offset_y={offset_y}")
    if direction == "EAST":
        x = ref.x + (ref.width / 2) + (target.width / 2) + distance + offset_x
        y = ref.y + offset_y
    elif direction == "WEST":
        x = ref.x - (ref.width / 2) - (target.width / 2) - distance + offset_x
        y = ref.y + offset_y
    elif direction == "NORTH":
        x = ref.x + offset_x
        y = ref.y + (ref.depth / 2) + (target.depth / 2) + distance + offset_y
    elif direction == "SOUTH":
        x = ref.x + offset_x
        y = ref.y - (ref.depth / 2) - (target.depth / 2) - distance + offset_y
    else:
        print(f"[Error] Unsupported direction {direction}")
        return

    z = target.height / 2
    calculate_position_and_bbox(target, x, y, z)
    overlaps, overlapping_obj = check_overlap_with_existing(target)
    max_tries = 5
    try_count = 0
    while overlaps and try_count < max_tries:
        print(f"[Warning] Overlap with {overlapping_obj} - adjusting {target_desc} attempt {try_count+1}")
        if direction in ["EAST", "WEST"]:
            y -= target.depth  # Shift SOUTH
        else:
            x += target.width if direction in ["NORTH"] else -target.width  # Shift EAST/WEST
        calculate_position_and_bbox(target, x, y, z)
        overlaps, overlapping_obj = check_overlap_with_existing(target)
        try_count += 1
    
    if overlaps or not within_room_boundaries(target):
        # Revert the object to its original state if it was previously placed
        if original_x is not None and original_y is not None and original_z is not None:
            target.x, target.y, target.z = original_x, original_y, original_z
            if original_bbox:
                target.bbox = original_bbox
            if overlaps:
                print(f"[Warning] Failed to place {target_desc} - object overlapping with {overlapping_obj}")
            else:
                 print(f"[Warning] Failed to place {target_desc} - object outside room constraints")
        else:
            # If it was not previously placed, reset coordinates to None
            target.x, target.y, target.z = None, None, None
            target.bbox = None
            if overlaps:
                print(f"[Warning] Failed to place {target_desc} - object overlapping with {overlapping_obj}")
            else:
                 print(f"[Warning] Failed to place {target_desc} - object outside room constraints")
        return

    # Successfully placed
    scene["constraints"].append(Constraint("PLACE_RELATIVE", {"target": target_desc, "reference": ref_desc, "direction": direction, "distance": distance, "offset_x": offset_x, "offset_y": offset_y}))
    print(f"[DSL] Placed {target_desc} at ({target.x:.2f}, {target.y:.2f}, {target.z:.2f})")
    save_scene()

def get_corner_position(obj, corner):
    if obj.x is None or obj.y is None:
        return None
    half_width = obj.width / 2
    half_depth = obj.depth / 2
    corners = {
        "NE": (obj.x + half_width, obj.y + half_depth),
        "NW": (obj.x - half_width, obj.y + half_depth),
        "SE": (obj.x + half_width, obj.y - half_depth),
        "SW": (obj.x - half_width, obj.y - half_depth)
    }
    return corners.get(corner)

def align_corners(target_desc, target_corner, ref_desc, ref_corner, distance):
    target = next((obj for obj in scene["objects"] if obj.description == target_desc), None)
    ref = next((obj for obj in scene["objects"] if obj.description == ref_desc), None)
    if not target or not ref:
        print(f"[Error] Object {target_desc} or {ref_desc} not found")
        return
    if ref.x is None or ref.y is None:
        print(f"[Error] Reference {ref_desc} must be placed first")
        return

    # Store original coordinates in case we need to revert
    original_x, original_y, original_z = target.x, target.y, target.z
    original_bbox = target.bbox.copy() if hasattr(target, 'bbox') and target.bbox else None

    print(f"[Debug] Aligning {target_desc} {target_corner} to {ref_desc} {ref_corner} with distance={distance}")
    ref_corner_pos = get_corner_position(ref, ref_corner)
    if ref_corner_pos is None:
        print(f"[Error] Invalid corner {ref_corner} for {ref_desc}")
        return
    R_x, R_y = ref_corner_pos

    diag = distance / math.sqrt(2)
    if target_corner == "SW" and ref_corner == "NE":
        dx, dy = -diag, -diag
    elif target_corner == "SE" and ref_corner == "NW":
        dx, dy = diag, -diag
    elif target_corner == "NW" and ref_corner == "SE":
        dx, dy = -diag, diag
    elif target_corner == "NE" and ref_corner == "SW":
        dx, dy = diag, diag
    else:
        print(f"[Warning] Using default offset for {target_corner}-{ref_corner}")
        dx, dy = -distance, -distance

    if target_corner == "SW":
        x = R_x + dx + target.width / 2
        y = R_y + dy + target.depth / 2
    elif target_corner == "SE":
        x = R_x + dx - target.width / 2
        y = R_y + dy + target.depth / 2
    elif target_corner == "NW":
        x = R_x + dx + target.width / 2
        y = R_y + dy - target.depth / 2
    elif target_corner == "NE":
        x = R_x + dx - target.width / 2
        y = R_y + dy - target.depth / 2
    else:
        print(f"[Error] Invalid target corner {target_corner}")
        return

    z = target.height / 2
    calculate_position_and_bbox(target, x, y, z)
    overlaps, overlapping_obj = check_overlap_with_existing(target)
    max_tries = 5
    try_count = 0
    while overlaps and try_count < max_tries:
        print(f"[Warning] Overlap with {overlapping_obj} - adjusting {target_desc} attempt {try_count+1}")
        if 'EAST' in target_corner:
            x += target.width
        elif 'WEST' in target_corner:
            x -= target.width
        if 'NORTH' in target_corner:
            y += target.depth
        elif 'SOUTH' in target_corner:
            y -= target.depth
        calculate_position_and_bbox(target, x, y, z)
        overlaps, overlapping_obj = check_overlap_with_existing(target)
        try_count += 1
    
    if overlaps or not within_room_boundaries(target):
        # Revert the object to its original state if it was previously placed
        if original_x is not None and original_y is not None and original_z is not None:
            target.x, target.y, target.z = original_x, original_y, original_z
            if original_bbox:
                target.bbox = original_bbox
            print(f"[Warning] Failed to place {target_desc} - reverted to original position")
        else:
            # If it was not previously placed, reset coordinates to None
            target.x, target.y, target.z = None, None, None
            target.bbox = None
            print(f"[Warning] Failed to place {target_desc} - object remains unplaced")
        return
        
    # Successfully placed
    scene["constraints"].append(Constraint("ALIGN_CORNERS", {"target": target_desc, "target_corner": target_corner, "reference": ref_desc, "reference_corner": ref_corner, "distance": distance}))
    print(f"[DSL] Placed {target_desc} at ({target.x:.2f}, {target.y:.2f}, {target.z:.2f})")
    save_scene()

def align_object(target_name, mode, target_anchor, ref_name, ref_anchor, offset=0.2, direction=None):
    target = next((obj for obj in scene["objects"] if obj.description == target_name), None)
    ref = next((obj for obj in scene["objects"] if obj.description == ref_name), None)

    if target is None or ref is None:
        print(f"[Error] One or both objects not found.")
        return
    if ref.x is None or ref.y is None:
        print(f"[Error] Reference '{ref_name}' must be placed before alignment.")
        return

    # Store original coordinates in case we need to revert
    original_x, original_y, original_z = target.x, target.y, target.z
    original_bbox = target.bbox.copy() if hasattr(target, 'bbox') and target.bbox else None

    def get_corner_pos(obj, anchor):
        hw, hd = obj.width / 2, obj.depth / 2
        return {
            "NW": (obj.x - hw, obj.y + hd),
            "NE": (obj.x + hw, obj.y + hd),
            "SW": (obj.x - hw, obj.y - hd),
            "SE": (obj.x + hw, obj.y - hd)
        }[anchor]

    def get_edge_pos(obj, anchor):
        hw, hd = obj.width / 2, obj.depth / 2
        return {
            "NORTH": (obj.x, obj.y + hd),
            "SOUTH": (obj.x, obj.y - hd),
            "EAST": (obj.x + hw, obj.y),
            "WEST": (obj.x - hw, obj.y)
        }[anchor]

    if mode == "corner":
        ref_pos = get_corner_pos(ref, ref_anchor)
    elif mode == "edge":
        ref_pos = get_edge_pos(ref, ref_anchor)
    else:
        print("[Error] Invalid mode. Use 'corner' or 'edge'.")
        return

    # Compute new target center based on alignment
    if mode == "corner":
        dx = {"N": 0, "S": 0, "E": offset, "W": -offset}
        dy = {"N": offset, "S": -offset, "E": 0, "W": 0}
        shift_x = dx[ref_anchor[1]]
        shift_y = dy[ref_anchor[0]]
        corner_x, corner_y = ref_pos[0] + shift_x, ref_pos[1] + shift_y

        # Compute center from corner
        center_offsets = {
            "NW": (target.width / 2, -target.depth / 2),
            "NE": (-target.width / 2, -target.depth / 2),
            "SW": (target.width / 2, target.depth / 2),
            "SE": (-target.width / 2, target.depth / 2)
        }
        cx, cy = center_offsets[target_anchor]
        new_x = corner_x + cx
        new_y = corner_y + cy
        z = target.height / 2
        calculate_position_and_bbox(target, new_x, new_y, z)
        
        # Check for overlaps and room boundaries
        overlaps, overlapping_obj = check_overlap_with_existing(target)
        max_tries = 5
        try_count = 0
        while overlaps and try_count < max_tries:
            print(f"[Warning] Overlap with {overlapping_obj} - adjusting {target_name} attempt {try_count+1}")
            if 'EAST' in target_anchor:
                new_x += target.width
            elif 'WEST' in target_anchor:
                new_x -= target.width
            if 'NORTH' in target_anchor:
                new_y += target.depth
            elif 'SOUTH' in target_anchor:
                new_y -= target.depth
            calculate_position_and_bbox(target, new_x, new_y, z)
            overlaps, overlapping_obj = check_overlap_with_existing(target)
            try_count += 1
        
        if overlaps or not within_room_boundaries(target):
            # Revert the object to its original state if it was previously placed
            if original_x is not None and original_y is not None and original_z is not None:
                target.x, target.y, target.z = original_x, original_y, original_z
                if original_bbox:
                    target.bbox = original_bbox
                print(f"[Warning] Failed to place {target_name} - reverted to original position")
            else:
                # If it was not previously placed, reset coordinates to None
                target.x, target.y, target.z = None, None, None
                target.bbox = None
                print(f"[Warning] Failed to place {target_name} - object remains unplaced")
            return
    else:  # edge
        # Define offset based on direction for side-by-side placement
        if direction:
            if ref_anchor in ["NORTH", "SOUTH"]:
                if direction == "EAST":
                    offset_x = ref.width / 2 + target.width / 2 + offset
                    offset_y = 0
                elif direction == "WEST":
                    offset_x = -(ref.width / 2 + target.width / 2 + offset)
                    offset_y = 0
                else:
                    print(f"[Error] Invalid direction '{direction}' for NORTH/SOUTH alignment. Use 'east' or 'west'.")
                    return
            elif ref_anchor in ["EAST", "WEST"]:
                if direction == "NORTH":
                    offset_x = 0
                    offset_y = ref.depth / 2 + target.depth / 2 + offset
                elif direction == "SOUTH":
                    offset_x = 0
                    offset_y = -(ref.depth / 2 + target.depth / 2 + offset)
                else:
                    print(f"[Error] Invalid direction '{direction}' for EAST/WEST alignment. Use 'north' or 'south'.")
                    return
        else:
            # Default offset (as before, but may cause overlap)
            edge_offset_directions = {
                "NORTH": (offset, 0),
                "SOUTH": (offset, 0),
                "EAST": (0, offset),
                "WEST": (0, offset)
            }
            offset_x, offset_y = edge_offset_directions[ref_anchor]

        tx, ty = ref_pos[0] + offset_x, ref_pos[1] + offset_y

        edge_offset = {
            "NORTH": (0, -target.depth / 2),
            "SOUTH": (0, target.depth / 2),
            "EAST": (-target.width / 2, 0),
            "WEST": (target.width / 2, 0)
        }[target_anchor]

        cx, cy = edge_offset
        x = tx + cx
        y = ty + cy
        z = target.height / 2
        calculate_position_and_bbox(target, x, y, z)
        
        # Check for overlaps and room boundaries
        overlaps, overlapping_obj = check_overlap_with_existing(target)
        if overlaps or not within_room_boundaries(target):
            # Revert the object to its original state if it was previously placed
            if original_x is not None and original_y is not None and original_z is not None:
                target.x, target.y, target.z = original_x, original_y, original_z
                if original_bbox:
                    target.bbox = original_bbox
                print(f"[Warning] Failed to place {target_name} - reverted to original position")
            else:
                # If it was not previously placed, reset coordinates to None
                target.x, target.y, target.z = None, None, None
                target.bbox = None
                print(f"[Warning] Failed to place {target_name} - object remains unplaced")
            return

    # Successfully placed
    scene["constraints"].append(Constraint("ALIGN_OBJECT", {"target": target_name, "mode": mode, "target_anchor": target_anchor, "reference": ref_name, "reference_anchor": ref_anchor, "offset": offset, "direction": direction}))
    print(f"[DSL] Aligned '{target_name}' {mode}({target_anchor}) to '{ref_name}' {mode}({ref_anchor}) with offset={offset} direction={direction}")
    save_scene()

# def place_in_room_corner(obj_desc, corner, wall_distance=0.2):
#     """Places an object in a specified corner of the room.
    
#     Args:
#         obj_desc: Description of the object to place
#         corner: Which corner - 'NE', 'NW', 'SE', 'SW'
#         wall_distance: Distance from the walls (default 0.2)
#     """
#     if not all([scene["room_width"], scene["room_depth"], scene["room_height"]]):
#         print("[Error] Room dimensions must be set before using place_in_room_corner")
#         return
        
#     obj = next((o for o in scene["objects"] if o.description == obj_desc), None)
#     if not obj:
#         print(f"[Error] Object {obj_desc} not found")
#         return
        
#     # Calculate position based on corner
#     half_width = obj.width / 2
#     half_depth = obj.depth / 2
    
#     if corner == "NE":
#         x = scene["room_width"] - half_width - wall_distance
#         y = scene["room_depth"] - half_depth - wall_distance
#     elif corner == "NW":
#         x = half_width + wall_distance
#         y = scene["room_depth"] - half_depth - wall_distance
#     elif corner == "SE":
#         x = scene["room_width"] - half_width - wall_distance
#         y = half_depth + wall_distance
#     elif corner == "SW":
#         x = half_width + wall_distance
#         y = half_depth + wall_distance
#     else:
#         print(f"[Error] Invalid corner {corner}, use 'NE', 'NW', 'SE', or 'SW'")
#         return
        
#     z = obj.height / 2
#     calculate_position_and_bbox(obj, x, y, z)
    
#     overlaps, overlapping_obj = check_overlap_with_existing(obj)
#     if overlaps:
#         print(f"[Warning] {obj_desc} overlaps with {overlapping_obj} - adjust manually")
        
#     scene["constraints"].append(Constraint("PLACE_ROOM_CORNER", 
#                                           {"object": obj_desc, "corner": corner, "wall_distance": wall_distance}))
#     print(f"[DSL] Placed {obj_desc} in room corner {corner} at ({x:.2f}, {y:.2f}, {z:.2f})")
#     save_scene()

def place_on_top(top_obj_desc, bottom_obj_desc, x_offset=0, y_offset=0, z_offset=0):
    """Places an object on top of another object.
    
    Args:
        top_obj_desc: Description of the object to place on top
        bottom_obj_desc: Description of the base object
        x_offset: Horizontal offset from center (default 0)
        y_offset: Depth offset from center (default 0)
        z_offset: Additional height offset (default 0)
    """
    top_obj = next((o for o in scene["objects"] if o.description == top_obj_desc), None)
    bottom_obj = next((o for o in scene["objects"] if o.description == bottom_obj_desc), None)
    
    if not top_obj or not bottom_obj:
        print(f"[Error] Object {top_obj_desc} or {bottom_obj_desc} not found")
        return
        
    if bottom_obj.x is None or bottom_obj.y is None:
        print(f"[Error] Base object {bottom_obj_desc} must be placed first")
        return
        
    # Check if top object fits on bottom object
    if top_obj.width > bottom_obj.width or top_obj.depth > bottom_obj.depth:
        print(f"[Warning] {top_obj_desc} is larger than {bottom_obj_desc} and may overhang")
        
    # Calculate position
    x = bottom_obj.x + x_offset
    y = bottom_obj.y + y_offset
    z = bottom_obj.z + (bottom_obj.height / 2) + (top_obj.height / 2) + z_offset
    
    calculate_position_and_bbox(top_obj, x, y, z)
    
    # We don't check overlaps for stacked objects since they're meant to overlap vertically
    
    scene["constraints"].append(Constraint("PLACE_ON_TOP", 
                               {"top": top_obj_desc, "bottom": bottom_obj_desc, 
                                "x_offset": x_offset, "y_offset": y_offset, "z_offset": z_offset}))
    print(f"[DSL] Placed {top_obj_desc} on top of {bottom_obj_desc} at ({x:.2f}, {y:.2f}, {z:.2f})")
    save_scene()

def mount_on_wall(obj_desc, wall, distance=0.05, position=0.5, height=None):
    """Mounts an object on a specified wall.
    
    Args:
        obj_desc: Description of the object to mount
        wall: Which wall - 'NORTH', 'EAST', 'SOUTH', 'WEST'
        distance: Distance from wall (default 0.05)
        position: Position along the wall (0.0 to 1.0, default 0.5 for middle)
        height: Height from floor (if None, uses 2/3 of room height)
    """
    if not all([scene["room_width"], scene["room_depth"], scene["room_height"]]):
        print("[Error] Room dimensions must be set before using mount_on_wall")
        return
        
    obj = next((o for o in scene["objects"] if o.description == obj_desc), None)
    if not obj:
        print(f"[Error] Object {obj_desc} not found")
        return
        
    # Set default mounting height if not specified
    if height is None:
        height = scene["room_height"] * (2/3)
    
    # Calculate position based on wall
    half_width = obj.width / 2
    half_depth = obj.depth / 2
    
    if wall == "NORTH":
        x = scene["room_width"] * position
        y = scene["room_depth"] - half_depth - distance
        facing = "SOUTH"
    elif wall == "EAST":
        x = scene["room_width"] - half_width - distance
        y = scene["room_depth"] * position
        facing = "WEST"
    elif wall == "SOUTH":
        x = scene["room_width"] * position
        y = half_depth + distance
        facing = "NORTH"
    elif wall == "WEST":
        x = half_width + distance
        y = scene["room_depth"] * position
        facing = "EAST"
    else:
        print(f"[Error] Invalid wall {wall}, use 'NORTH', 'EAST', 'SOUTH', or 'WEST'")
        return
        
    z = height
    calculate_position_and_bbox(obj, x, y, z)
    obj.facing = facing
    
    overlaps, overlapping_obj = check_overlap_with_existing(obj)
    if overlaps:
        print(f"[Warning] {obj_desc} overlaps with {overlapping_obj} - adjust manually")
        
    scene["constraints"].append(Constraint("MOUNT_ON_WALL", 
                               {"object": obj_desc, "wall": wall, 
                                "distance": distance, "position": position, "height": height}))
    print(f"[DSL] Mounted {obj_desc} on {wall} wall at ({x:.2f}, {y:.2f}, {z:.2f}) facing {facing}")
    save_scene()

def move_object(obj_desc, direction, distance):
    """Moves an object in the specified direction by a given distance.
    
    Args:
        obj_desc: Description of the object to move
        direction: Direction to move - 'NORTH', 'EAST', 'SOUTH', 'WEST'
        distance: Distance to move in meters
    """
    obj = next((o for o in scene["objects"] if o.description == obj_desc), None)
    if not obj:
        print(f"[Error] Object {obj_desc} not found")
        return
        
    if obj.x is None or obj.y is None:
        print(f"[Error] Object {obj_desc} must be placed before moving")
        return
        
    # Calculate new position based on direction
    if direction == "NORTH":
        obj.y += distance
    elif direction == "EAST":
        obj.x += distance
    elif direction == "SOUTH":
        obj.y -= distance
    elif direction == "WEST":
        obj.x -= distance
    else:
        print(f"[Error] Invalid direction {direction}, use 'NORTH', 'EAST', 'SOUTH', or 'WEST'")
        return
        
    # Update bounding box
    calculate_position_and_bbox(obj, obj.x, obj.y, obj.z)
    
    overlaps, overlapping_obj = check_overlap_with_existing(obj)
    if overlaps:
        print(f"[Warning] {obj_desc} now overlaps with {overlapping_obj} after moving")
        
    if not within_room_boundaries(obj):
        print(f"[Warning] {obj_desc} is now outside room boundaries after moving")
        
    scene["constraints"].append(Constraint("MOVE", 
                               {"object": obj_desc, "direction": direction, "distance": distance}))
    print(f"[DSL] Moved {obj_desc} {direction} by {distance}m to ({obj.x:.2f}, {obj.y:.2f}, {obj.z:.2f})")
    save_scene()

def rotate_object(obj_desc, turns=1):
    """Rotates an object by 90-degree increments clockwise.
    
    Args:
        obj_desc: Description of the object to rotate
        turns: Number of 90-degree turns clockwise (default 1)
    """
    obj = next((o for o in scene["objects"] if o.description == obj_desc), None)
    if not obj:
        print(f"[Error] Object {obj_desc} not found")
        return
        
    if obj.x is None or obj.y is None:
        print(f"[Error] Object {obj_desc} must be placed before rotating")
        return
    
    # Store original position and dimensions
    original_x, original_y = obj.x, obj.y
    original_width, original_depth = obj.width, obj.depth
    
    # Normalize turns to 0-3 range
    turns = turns % 4
    if turns == 0:
        print(f"[Info] No rotation needed (0 degrees)")
        return
    
    # Update facing direction
    facings = ["NORTH", "EAST", "SOUTH", "WEST"]
    current_facing_index = facings.index(obj.facing)
    new_facing_index = (current_facing_index + turns) % 4
    obj.facing = facings[new_facing_index]
    
    # Update rotation value (0, 90, 180, 270)
    obj.rotation = (obj.rotation + turns * 90) % 360
    
    # Calculate new center coordinates based on rotation
    # For 90-degree rotations, we can use a simplified approach:
    if turns % 2 == 1:  # 90 or 270 degrees - width and depth are flipped in layout
        if original_width != original_depth:
            # Calculate offset for new object center
            width_diff = original_width - original_depth
            depth_diff = original_depth - original_width
            
            # Adjust based on rotation direction
            if obj.rotation == 90:  # Clockwise once
                obj.x = original_x + depth_diff/2
                obj.y = original_y + width_diff/2
            elif obj.rotation == 270:  # Clockwise three times (counter-clockwise once)
                obj.x = original_x - depth_diff/2
                obj.y = original_y - width_diff/2
    elif turns == 2:  # 180 degrees - dimensions remain same, but position may change
        # No center adjustment needed for 180-degree rotation if width=depth
        pass
    
    # Now calculate the rotated bounding box with the new center coordinates
    calculate_rotated_bbox(obj)
    
    # Check for collisions with the new position and bbox
    overlaps, overlapping_obj = check_overlap_with_existing(obj)
    if overlaps:
        print(f"[Warning] {obj_desc} now overlaps with {overlapping_obj} after rotation")
        
    if not within_room_boundaries(obj):
        print(f"[Warning] {obj_desc} is now outside room boundaries after rotation")
    
    scene["constraints"].append(Constraint("ROTATE", 
                              {"object": obj_desc, "turns": turns}))
    print(f"[DSL] Rotated {obj_desc} {turns*90} degrees clockwise to face {obj.facing}")
    print(f"[DSL] New center position: ({obj.x:.2f}, {obj.y:.2f})")
    save_scene()

def calculate_rotated_bbox(obj):
    """Calculate bounding box for a rotated object."""
    x, y, z = obj.x, obj.y, obj.z
    half_width = float(obj.width) / 2
    half_depth = float(obj.depth) / 2
    half_height = float(obj.height) / 2
    
    # Determine rotation angle in radians
    angle_rad = math.radians(obj.rotation)
    
    # Calculate the corners of the bounding box (before rotation, around origin)
    corners = [
        [-half_width, -half_depth],  # back-left
        [half_width, -half_depth],   # back-right
        [half_width, half_depth],    # front-right
        [-half_width, half_depth],   # front-left
    ]
    
    # Apply rotation around the origin, then translate to final position
    rotated_corners = []
    for corner_x, corner_y in corners:
        # Apply rotation
        rx = corner_x * math.cos(angle_rad) - corner_y * math.sin(angle_rad)
        ry = corner_x * math.sin(angle_rad) + corner_y * math.cos(angle_rad)
        
        # Translate to final position
        rotated_corners.append([rx + x, ry + y])
    
    # Find the min and max x, y coordinates for the axis-aligned bounding box
    min_x = min(corner[0] for corner in rotated_corners)
    max_x = max(corner[0] for corner in rotated_corners)
    min_y = min(corner[1] for corner in rotated_corners)
    max_y = max(corner[1] for corner in rotated_corners)
    
    # Update the object's bounding box
    obj.bbox = {
        "x": [min_x, max_x],
        "y": [min_y, max_y],
        "z": [z - half_height, z + half_height]
    }
    
    print(f"[Debug] Rotated {obj.description} at ({x:.2f}, {y:.2f}, {z:.2f})")
    print(f"[Debug] Rotated BBox: x=[{min_x:.2f}, {max_x:.2f}], y=[{min_y:.2f}, {max_y:.2f}]")
    
def place_in_room_corner(obj_desc, corner, wall_distance=0.2, facing=None):
    """Places an object in a specified corner of the room using its final rotated extents."""
    # sanity checks
    if not all([scene["room_width"], scene["room_depth"], scene["room_height"]]):
        print("[Error] Room dimensions must be set before using place_in_room_corner")
        return
    obj = next((o for o in scene["objects"] if o.description == obj_desc), None)
    if not obj:
        print(f"[Error] Object {obj_desc} not found")
        return
    
    # default facing by corner
    if facing is None :
        facing = {"NE":"WEST", "NW":"EAST", "SE":"WEST", "SW":"EAST"}.get(corner, "NORTH")
    facings = ["NORTH","EAST","SOUTH","WEST"]
    if facing not in facings or corner not in ["NE","NW","SE","SW"]:
        print(f"[Error] Invalid corner/facing: {corner}, {facing}")
        return
    
    # Calculate number of turns needed to reach the target facing
    original_facing = "NORTH"
    turns = (facings.index(facing) - facings.index(original_facing)) % 4
    
    # Calculate position based on corner and facing
    if facing in ["EAST", "WEST"]:  # 90° or 270° rotation
        # After rotation, width and depth will be swapped in the scene
        place_width = obj.depth
        place_depth = obj.width
    else:  # 0° or 180° rotation (NORTH or SOUTH)
        place_width = obj.width
        place_depth = obj.depth
    
    # Calculate center position based on corner and post-rotation dimensions
    if corner == "SW":  # Southwest corner (origin)
        x = wall_distance + (place_width / 2)
        y = wall_distance + (place_depth / 2)
    elif corner == "SE":  # Southeast corner
        x = scene["room_width"] - wall_distance - (place_width / 2)
        y = wall_distance + (place_depth / 2)
    elif corner == "NW":  # Northwest corner
        x = wall_distance + (place_width / 2)
        y = scene["room_depth"] - wall_distance - (place_depth / 2)
    elif corner == "NE":  # Northeast corner
        x = scene["room_width"] - wall_distance - (place_width / 2)
        y = scene["room_depth"] - wall_distance - (place_depth / 2)
    
    # height is always half the object's height
    z = obj.height / 2
    
    # Set position
    obj.x, obj.y, obj.z = x, y, z
    
    # Set rotation properties
    obj.facing = facing
    obj.rotation = turns * 90
    
    # Calculate bounding box with the position and rotation
    calculate_position_and_bbox(obj, x, y, z)
    
    # Checks
    overlaps, other = check_overlap_with_existing(obj)
    if overlaps:
        print(f"[Warning] {obj_desc} overlaps with {other}")
    if not within_room_boundaries(obj):
        print(f"[Warning] {obj_desc} out of bounds")
    
    # Record constraint & save
    scene["constraints"].append(
        Constraint("PLACE_ROOM_CORNER",
                  {"object": obj_desc,
                   "corner": corner,
                   "wall_distance": wall_distance,
                   "facing": facing})
    )
    print(f"[DSL] Placed {obj_desc} at ({x:.2f},{y:.2f},{z:.2f}) in {corner}, facing {facing}")
    save_scene()
    
def place_along_wall(obj_desc, wall, position=0.5, wall_distance=0.2):
    """Places an object along a specified wall.
    
    Args:
        obj_desc: Description of the object to place
        wall: Which wall - 'NORTH', 'EAST', 'SOUTH', 'WEST'
        position: Position along the wall (0.0 to 1.0, default 0.5 for middle)
        wall_distance: Distance from the wall (default 0.2)
    """
    if not all([scene["room_width"], scene["room_depth"], scene["room_height"]]):
        print("[Error] Room dimensions must be set before using place_along_wall")
        return
        
    obj = next((o for o in scene["objects"] if o.description == obj_desc), None)
    if not obj:
        print(f"[Error] Object {obj_desc} not found")
        return
        
    # Calculate position based on wall
    half_width = obj.width / 2
    half_depth = obj.depth / 2
    
    if wall == "NORTH":
        x = scene["room_width"] * position
        y = scene["room_depth"] - half_depth - wall_distance
        facing = "SOUTH"
    elif wall == "EAST":
        x = scene["room_width"] - half_width - wall_distance
        y = scene["room_depth"] * position
        facing = "WEST"
    elif wall == "SOUTH":
        x = scene["room_width"] * position
        y = half_depth + wall_distance
        facing = "NORTH"
    elif wall == "WEST":
        x = half_width + wall_distance
        y = scene["room_depth"] * position
        facing = "EAST"
    else:
        print(f"[Error] Invalid wall {wall}, use 'NORTH', 'EAST', 'SOUTH', or 'WEST'")
        return
        
    z = obj.height / 2
    calculate_position_and_bbox(obj, x, y, z)
    obj.facing = facing
    
    overlaps, overlapping_obj = check_overlap_with_existing(obj)
    if overlaps:
        print(f"[Warning] {obj_desc} overlaps with {overlapping_obj} - adjust manually")
        
    scene["constraints"].append(Constraint("PLACE_ALONG_WALL", 
                               {"object": obj_desc, "wall": wall, 
                                "position": position, "wall_distance": wall_distance}))
    print(f"[DSL] Placed {obj_desc} along {wall} wall at ({x:.2f}, {y:.2f}, {z:.2f}) facing {facing}")
    save_scene()

def arrange_in_group(obj_descs, formation="circle", center_x=None, center_y=None, height=None, spacing=0.5, facing="inward"):
    """Arranges multiple objects in a specified formation.
    
    Args:
        obj_descs: List of object descriptions to arrange
        formation: "circle", "row", or "semicircle" (default "circle")
        center_x: X-coordinate of formation center (default room center)
        center_y: Y-coordinate of formation center (default room center)
        height: Z-coordinate height for all objects (default None, which uses object's own height/2)
        spacing: Space between objects (default 0.5)
        facing: Where objects face - "inward", "outward", "same" (default "inward")
    """
    if not all([scene["room_width"], scene["room_depth"]]):
        print("[Error] Room dimensions must be set before using arrange_in_group")
        return
        
    objs = [next((o for o in scene["objects"] if o.description == desc), None) for desc in obj_descs]
    if None in objs:
        print(f"[Error] One or more objects not found")
        return
        
    # Set default center to room center if not specified
    if center_x is None:
        center_x = scene["room_width"] / 2
    if center_y is None:
        center_y = scene["room_depth"] / 2
        
    # Calculate positions based on formation
    count = len(objs)
    
    if formation == "circle":
        # Calculate radius based on object sizes and spacing
        max_dimension = max([max(float(obj.width), float(obj.depth)) for obj in objs])
        radius = (count * max_dimension + count * spacing) / (2 * math.pi)
        radius = max(radius, 0.5)  # Minimum radius
        
        for i, obj in enumerate(objs):
            angle = 2 * math.pi * i / count
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            # Use specified height if provided, otherwise use object's half height
            z = height if height is not None else float(obj.height) / 2
            
            calculate_position_and_bbox(obj, x, y, z)
            
            # Set facing direction
            if facing == "inward":
                obj.facing = "NORTH" if y < center_y else "SOUTH" if y > center_y else "EAST" if x < center_x else "WEST"
            elif facing == "outward":
                obj.facing = "SOUTH" if y < center_y else "NORTH" if y > center_y else "WEST" if x < center_x else "EAST"
            
            overlaps, overlapping_obj = check_overlap_with_existing(obj)
            if overlaps:
                print(f"[Warning] {obj.description} overlaps with {overlapping_obj} - adjust manually")
    
    elif formation == "row":
        row_width = sum([float(obj.width) for obj in objs]) + spacing * (count - 1)
        start_x = center_x - row_width / 2
        
        current_x = start_x
        for obj in objs:
            x = current_x + float(obj.width) / 2
            y = center_y
            # Use specified height if provided, otherwise use object's half height
            z = height if height is not None else float(obj.height) / 2
            
            calculate_position_and_bbox(obj, x, y, z)
            
            # Set facing direction
            if facing == "same":
                obj.facing = "NORTH"
            
            overlaps, overlapping_obj = check_overlap_with_existing(obj)
            if overlaps:
                print(f"[Warning] {obj.description} overlaps with {overlapping_obj} - adjust manually")
                
            current_x += float(obj.width) + spacing
    
    elif formation == "semicircle":
        # Calculate radius similar to circle but for half-circle
        max_dimension = max([max(float(obj.width), float(obj.depth)) for obj in objs])
        radius = (count * max_dimension + count * spacing) / math.pi
        radius = max(radius, 1.0)  # Minimum radius
        
        for i, obj in enumerate(objs):
            angle = math.pi * i / (count - 1)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            # Use specified height if provided, otherwise use object's half height
            z = height if height is not None else float(obj.height) / 2
            
            calculate_position_and_bbox(obj, x, y, z)
            
            # Set facing direction
            if facing == "inward":
                obj.facing = "NORTH" if y < center_y else "SOUTH" if y > center_y else "EAST" if x < center_x else "WEST"
            elif facing == "outward":
                obj.facing = "SOUTH" if y < center_y else "NORTH" if y > center_y else "WEST" if x < center_x else "EAST"
            
            overlaps, overlapping_obj = check_overlap_with_existing(obj)
            if overlaps:
                print(f"[Warning] {obj.description} overlaps with {overlapping_obj} - adjust manually")
    
    scene["constraints"].append(Constraint("ARRANGE_IN_GROUP", 
                               {"objects": obj_descs, "formation": formation, 
                                "center_x": center_x, "center_y": center_y, 
                                "height": height, "spacing": spacing, "facing": facing}))
    print(f"[DSL] Arranged {len(obj_descs)} objects in {formation} formation")
    save_scene()

def place_relative_multi(target_desc, ref_descs, directions, distances):
    target = next((obj for obj in scene["objects"] if obj.description == target_desc), None)
    refs = [next((obj for obj in scene["objects"] if obj.description == d), None) for d in ref_descs]
    if not target or None in refs:
        print(f"[Error] Object {target_desc} or references {ref_descs} not found")
        return
    if any(ref.x is None or ref.y is None for ref in refs):
        print(f"[Error] All references {ref_descs} must be placed first")
        return

    print(f"[Debug] Placing {target_desc} relative to {ref_descs} with directions={directions}, distances={distances}")
    total_x, total_y = 0, 0
    count = 0
    for ref, direction, distance in zip(refs, directions, distances):
        if direction == "EAST":
            x = ref.x + (ref.width / 2) + (target.width / 2) + distance
            y = ref.y
        elif direction == "WEST":
            x = ref.x - (ref.width / 2) - (target.width / 2) - distance
            y = ref.y
        elif direction == "NORTH":
            x = ref.x
            y = ref.y + (ref.depth / 2) + (target.depth / 2) + distance
        elif direction == "SOUTH":
            x = ref.x
            y = ref.y - (ref.depth / 2) - (target.depth / 2) - distance
        else:
            print(f"[Error] Unsupported direction {direction}")
            return
        total_x += x
        total_y += y
        count += 1
        print(f"[Debug] {direction} from {ref.description}: ({x:.2f}, {y:.2f})")

    x = total_x / count
    y = total_y / count
    z = target.height / 2
    calculate_position_and_bbox(target, x, y, z)
    overlaps, overlapping_obj = check_overlap_with_existing(target)
    max_tries = 5
    try_count = 0
    while overlaps and try_count < max_tries:
        print(f"[Warning] Overlap with {overlapping_obj} - adjusting {target_desc} attempt {try_count+1}")
        x += target.width  # Try EAST
        y -= target.depth  # Try SOUTH
        calculate_position_and_bbox(target, x, y, z)
        overlaps, overlapping_obj = check_overlap_with_existing(target)
        try_count += 1
    if overlaps:
        print(f"[Error] Could not place {target_desc} without overlap after {max_tries} tries")
    if not within_room_boundaries(target):
        print(f"[Warning] {target_desc} out of bounds - adjust manually")
    scene["constraints"].append(Constraint("PLACE_RELATIVE_MULTI", {"target": target_desc, "references": ref_descs, "directions": directions, "distances": distances}))
    print(f"[DSL] Placed {target_desc} at ({target.x:.2f}, {target.y:.2f}, {target.z:.2f})")
    save_scene()

