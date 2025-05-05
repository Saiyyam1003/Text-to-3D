import os
import sys
import json
import tensorflow as tf
from transformers import BertTokenizer, TFBertModel

def initialize_scene(scene_file="scene_state.json"):
    """Initialize an empty scene_state.json with no content."""
    try:
        with open(scene_file, "w") as f:
            json.dump({}, f, indent=4)
        print(f"New empty scene initialized: {scene_file} created.")
        return True
    except Exception as e:
        print(f"[Error] Failed to create {scene_file}: {str(e)}")
        return False

def load_scene(scene_file="scene_state.json"):
    """Load an existing scene_state.json file."""
    try:
        with open(scene_file, "r") as f:
            scene_data = json.load(f)
        print(f"Scene loaded successfully from {scene_file}.")
        return True
    except FileNotFoundError:
        print(f"[Error] Scene file '{scene_file}' not found.")
        return False
    except json.JSONDecodeError:
        print(f"[Error] Invalid JSON format in '{scene_file}'.")
        return False

def main():
    """
    Main function for the natural language to 3D scene pipeline.

    Prompts user to load an existing scene or create a new empty one, classifies the command type,
    generates the DSL command, and executes it to update the scene graph.
    """
    zip_path = '/content/my_command_classifier_model.zip'  # Path to the ZIP file
    extract_path = '/content/my_command_classifier_model'  # Directory to extract to


    # Import the modules here to avoid conflicts
    import dsl_class
    import nlp
    import dsl
    import nlc
    import time
    dsl.scene = {"objects": [], "constraints": [], "room_width": None, "room_depth": None, "room_height": None}
    # Prompt user to load or create a scene
    print("\nWelcome to the 3D Scene Generator!")
    print("Would you like to:")
    print("1. Load an existing scene")
    print("2. Create a new scene")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        scene_file = input("Enter the path to the scene file (default: scene_state.json): ").strip() or "scene_state.json"
        if not load_scene(scene_file):
            print("Falling back to creating a new empty scene.")
            if not initialize_scene(scene_file):
                print("[Error] Failed to initialize a new scene. Exiting.")
                return
    elif choice == "2":
        scene_file = input("Enter the path for the new scene file (default: scene_state.json): ").strip() or "scene_state.json"
        if not initialize_scene(scene_file):
            print("[Error] Failed to initialize a new scene. Exiting.")
            return
    else:
        print("[Error] Invalid choice. Exiting.")
        return

    # Initialize the BERT tokenizer and load the model
    print("Initializing models...")
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    model = tf.keras.models.load_model(
        extract_path,  # Load from the unzipped directory
        custom_objects={'TFBertModel': TFBertModel}
    )
    try:
        model.load_weights('command_classifier/variables/variables').expect_partial()
        print("Model weights loaded successfully.")
    except Exception as e:
        print(f"Warning: Error loading model weights - {e}")
        print("Continuing with uninitialized model for demonstration...")

    print("\nEnter natural language commands to build your scene, or 'exit' to quit.")
    print("Example: 'Create a room with dimensions 5x5x3 meters'")

    # Create a namespace for DSL execution that includes all DSL functions
    dsl_namespace = {}
    for name in dir(dsl):
        if not name.startswith("__"):
            dsl_namespace[name] = getattr(dsl, name)

    while True:
        # Get user input
        user_input = input("\nEnter command (or 'exit' to quit): ")

        if user_input.lower() in ['exit', 'quit', 'bye']:
            break

        try:
            start_time = time.time()

            # Step 1: Classify the command type using dsl_classifier
            command_type = dsl_class.predict_dsl(user_input, model, tokenizer)
            print(f"Classified command type: {command_type}")

            # Step 2: Generate the DSL command string using nlp.py
            nlp_function = getattr(nlp, command_type)
            dsl_command_str = nlp_function(user_input)
            print(f"Generated DSL command: {dsl_command_str}")

            # Step 3: Execute the DSL command
            exec(dsl_command_str, {}, dsl_namespace)
            print("Command executed successfully!")
            visualize_scene(scene_file)
            end_time = time.time()
            print(f"Time taken: {end_time - start_time:.2f} seconds")
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again with a different command.")

    print("\nExiting the scene generator. Goodbye!")

    # Ask if the user wants to transform the scene for import
    # if input("\nDo you want to transform the scene for import? (y/n): ").lower() == 'y':
    #     # Use the scene_file chosen earlier
    #     input_dir = input("Enter path to input 3D models: ")
    #     output_dir = input("Enter path for transformed models: ")

    #     # Make sure the output Euras the output directory exists
    #     os.makedirs(output_dir, exist_ok=True)

    #     try:
    #         # Process the scene using sc.py
    #         sc.process_scene(scene_file, input_dir, output_dir)
    #         print("Scene transformed and ready for import!")
    #     except Exception as e:
    #         print(f"Error transforming scene: {str(e)}")

    print("Thank you for using the 3D Scene Generator!")

if __name__ == "__main__":
    main()