import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Needed for 3D projection, even if unused

def visualize_scene(json_file):
    """Visualize the 3D scene from a JSON scene file using Matplotlib, non-blocking."""
    try:
        with open(json_file, "r") as f:
            scene_data = json.load(f)
    except FileNotFoundError:
        print(f"[Error] JSON file '{json_file}' not found.")
        return
    except json.JSONDecodeError:
        print(f"[Error] Invalid JSON format in '{json_file}'.")
        return

    room = scene_data.get("room", {})
    room_width = room.get("width", 0)
    room_length = room.get("depth", 0)
    room_height = room.get("height", 0)
    if not (room_width and room_length and room_height):
        print("[Error] Room dimensions missing or invalid in JSON.")
        return

    # Create figure and 3D axes
    plt.ion()  # Enable interactive mode for non-blocking
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot room outline (wireframe)
    r = [-room_width/2, room_width/2]
    s = [-room_length/2, room_length/2]
    t = [0, room_height]
    for x in r:
        for y in s:
            ax.plot3D([x, x], [y, y], t, 'g')
    for z in t:
        for x in r:
            ax.plot3D([x, x], s, [z, z], 'g')
        for y in s:
            ax.plot3D(r, [y, y], [z, z], 'g')

    # Plot objects (bounding boxes)
    for obj in scene_data.get("objects", []):
        if obj["x"] is None or obj["y"] is None or obj["z"] is None:
            print(f"[Warning] Skipping {obj['description']} due to missing coordinates.")
            continue

        x_center = obj["x"] - room_width / 2
        y_center = obj["y"] - room_length / 2
        z_center = obj["z"]
        width = obj["width"]
        depth = obj["depth"]
        height = obj["height"]
        rotation = obj["rotation"] * (np.pi / 180)

        dx = width / 2
        dy = depth / 2
        dz = height / 2
        vertices = np.array([
            [dx, dy, dz], [dx, dy, -dz], [dx, -dy, dz], [dx, -dy, -dz],
            [-dx, dy, dz], [-dx, dy, -dz], [-dx, -dy, dz], [-dx, -dy, -dz]
        ])

        rot_matrix = np.array([
            [np.cos(rotation), -np.sin(rotation), 0],
            [np.sin(rotation), np.cos(rotation), 0],
            [0, 0, 1]
        ])
        vertices = vertices @ rot_matrix.T
        vertices += [x_center, y_center, z_center]

        edges = [
            [0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3],
            [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7]
        ]

        for edge in edges:
            x = vertices[edge, 0]
            y = vertices[edge, 1]
            z = vertices[edge, 2]
            ax.plot3D(x, y, z, 'r')

        ax.text(x_center, y_center, z_center, obj["description"], color='black')

    ax.set_xlabel('X (Width)')
    ax.set_ylabel('Y (Length)')
    ax.set_zlabel('Z (Height)')
    ax.set_title('3D Scene Visualization')

    max_range = max(room_width, room_length, room_height) * 1.5
    ax.set_xlim(-max_range/2, max_range/2)
    ax.set_ylim(-max_range/2, max_range/2)
    ax.set_zlim(0, max_range)

    # Draw and pause briefly to show the plot, then close
    plt.draw()
    
    plt.pause(20)  # Show plot for 2 seconds
    # plt.close(fig)  # Close to allow input


visualize_scene('scene_state.json')