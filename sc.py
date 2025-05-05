import trimesh
import numpy as np
import json
import os

def transform_glb(input_path, output_path, params):
    mesh = trimesh.load(input_path, process=False, force='mesh')
    
    # First, center the mesh
    mesh.apply_translation(-mesh.bounding_box.center_mass)
    
    # Get original dimensions
    original_dims = mesh.bounding_box.extents
    
    # Calculate scaling factors
    scale_factors = [
        params['length'] / original_dims[0],  # x: length (Blender x)
        params['height'] / original_dims[1],  # y: height (Blender z)
        params['width'] / original_dims[2]    # z: width (Blender y)
    ]
    
    # Create and apply scaling transformation
    scale_transform = np.eye(4)
    scale_transform[:3, :3] = np.diag(scale_factors)
    mesh.apply_transform(scale_transform)
    
    # Now apply facing direction rotation
    facing = params.get('facing', 'NORTH')
    rotation_angle = {
        'NORTH': 0,    # Front (+z) to +y
        'SOUTH': 180,  # Front (+z) to -y
        'EAST': -90,   # Front (+z) to +x
        'WEST': 90     # Front (+z) to -x
    }.get(facing, 0)  # Default to NORTH
    
    rotation = trimesh.transformations.rotation_matrix(
        np.radians(rotation_angle),
        [0, 1, 0]  # Rotate around y-axis
    )
    mesh.apply_transform(rotation)
    
    # Translate to desired position
    translation = np.eye(4)
    translation[:3, 3] = [params['x'], params['z'], params['y']]
    mesh.apply_transform(translation)
    
    # MIRROR along YZ plane (flip X-axis)
    mirror = np.eye(4)
    mirror[0, 0] = -1  # Flip the X component
    mesh.apply_transform(mirror)
    
    # Debug information
    final_center = mesh.bounding_box.center_mass
    expected_center = [-params['x'], params['z'], params['y']]  # X is now negative due to mirroring
    print(f"Final center for {params['description']}: {final_center}, Expected: {expected_center}")
    
    # Export transformed mesh
    mesh.export(output_path)

def process_scene(scene_file, input_dir, output_dir):
    # Load JSON
    with open(scene_file, 'r') as f:
        scene = json.load(f)

    # Process each object
    for obj in scene['objects']:
        params = {
            'description': obj['description'],
            'length': obj['width'],   # Blender x-axis
            'width': obj['depth'],    # Blender y-axis
            'height': obj['height'],  # Blender z-axis
            'x': obj['x'],
            'y': obj['y'],
            'z': obj['z'],
            'facing': obj['facing']
        }

        input_path = os.path.join(input_dir, f"{obj['description']}.glb")
        output_path = os.path.join(output_dir, f"transformed_{obj['description']}.glb")

        if os.path.exists(input_path):
            print(f"Transforming {obj['description']}...")
            transform_glb(input_path, output_path, params)
        else:
            print(f"Warning: {input_path} not found")

# Paths
scene_file = "scene_state.json"
input_dir = 'path_to_your_input_dir_where_objects_are_stored'
output_dir = 'path_to_the_output_dir'

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Process the scene
process_scene(scene_file, input_dir, output_dir)