# Text-to-3D Scene Generation with NLP-Powered Object Placement

## Overview

This project implements a natural language-driven 3D scene generation system that enables users to create and manipulate virtual environments through simple text commands. The system interprets natural language instructions, converts them to a domain-specific language (DSL), and executes spatial operations in a 3D environment, with intelligent object placement and constraint handling.

![System Architecture](images/architecture.png)

- **Natural Language Understanding**: Process free-form text instructions for scene manipulation
- **Domain-Specific Language**: Convert natural language to executable DSL commands
- **Intelligent Object Placement**: Automatically handle spatial constraints and object relationships
- **Scene Graph Management**: Maintain a consistent representation of the 3D environment
- **Style Classification**: Use an agentic LLM to determine appropriate object styles and architecture
- **Blender Integration**: Render realistic 3D scenes with proper scaling and transforms

## System Architecture

The pipeline consists of several key components:

1. **User Input Processing**: Natural language text is analyzed to determine user intent
2. **DSL Command Classification**: The system classifies the input into appropriate command types
3. **Parameter Extraction**: Key spatial parameters (distances, directions, relationships) are identified
4. **DSL Command Generation**: Structured commands are generated for scene manipulation
5. **Scene Graph Update**: The internal representation of the scene is modified based on commands
6. **Constraint Handling**: System checks for overlaps and spatial constraints
7. **Object Retrieval**: Compatible 3D objects are sourced from Objaverse based on style requirements
8. **Scene Rendering**: Final scene is rendered in Blender with proper object scaling and transformations

## Command Capabilities

The system supports various scene manipulation operations including:

- Object placement (e.g., "place a chair in front of the sofa")
- Object movement (e.g., "move the chair to the left")
- Distance specifications (e.g., "by 0.6m")
- Spatial relationships (e.g., "in front of", "next to")
- Scene rearrangement with collision detection and constraint satisfaction

## Implementation Details

- **DSL Executor**: Translates high-level commands into specific 3D transformations
- **Collision Detection**: Identifies and resolves object overlaps
- **Spatial Reasoning**: Places objects according to human-intuitive spatial relationships
- **Room Constraints**: Ensures objects remain within valid scene boundaries
- **Agentic LLM**: Determines appropriate styles and architectural elements for coherent scenes

## Examples
![test case 1](images/test_case_1.png)

### Example 1: Moving Objects

**Input**: "Move the chair to the left by some distance"  
**Output**: System attempts placement with collision detection and constraint satisfaction

![test case 2](images/test_case_2.png)
### Example 2: Placing Objects with Relationships

**Input**: "Place a chair in front of the sofa by 0.6m"  
**Output**: System calculates appropriate position, handles potential collisions, and places the chair at the specified location


## Future Work

- Integration with more advanced rendering engines
- Support for more complex spatial relationships
- Enhanced object style matching
- User interface improvements
- Expansion of the DSL vocabulary

