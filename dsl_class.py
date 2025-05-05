import json
import os
import re
import numpy as np
import zipfile
from transformers import BertTokenizer, TFBertModel
import tensorflow as tf

# Define command types
command_types = [
    'place_along_wall', 'place_relative', 'create_object', 'align_object', 'place_on_top',
    'arrange_in_group', 'set_room', 'rotate_object', 'mount_on_wall', 'place_relative_multi',
    'move_object', 'place_in_room_corner'
]
label_to_command = {i: cmd for i, cmd in enumerate(command_types)}

# Keyword set for embeddings
keywords = [
    'along the wall', 'parallel to', 'beside the wall',  # place_along_wall
    'to the', 'south of', 'north of', 'east of', 'west of', 'southward',  # place_relative
    'create', 'construct', 'with dimensions',  # create_object
    'align', 'matching', 'in line with', 'edge',  # align_object
    'on top', 'on', 'above',  # place_on_top
    'arrange', 'in a group', 'together', 'pattern',  # arrange_in_group
    'set the room', 'room to', 'room dimensions',  # set_room
    'rotate', 'turn', 'by degrees', 'orient',  # rotate_object
    'mount', 'on the wall', 'hang', 'install',  # mount_on_wall
    'place multiple', 'relative to', 'position near',  # place_relative_multi
    'move', 'shift', 'relocate',  # move_object
    'in the corner', 'at the corner', 'room corner'  # place_in_room_corner
]

# Enhanced keyword embedding with multi-object detection
def is_multi_object(nlp_input):
    """Detects if command involves multiple objects"""
    nlp_lower = nlp_input.lower()
    if re.search(r'\band\b', nlp_lower) or re.search(r',\s*\w+', nlp_lower):
        return True  # Matches "a, b, and c" patterns
    if re.search(r'\b(two|three|four|five|six|seven|eight|nine|ten|multiple|several)\b', nlp_lower):
        return True  # Matches quantity words
    return False

def create_keyword_embedding(nlp_input):
    """Enhanced embedding with alignment, corner, and multi-object flags"""
    embedding = np.zeros(len(keywords) + 3)  # Original + align + corner + multi-object
    nlp_lower = nlp_input.lower()
    
    # Base keywords
    for i, keyword in enumerate(keywords):
        if keyword in nlp_lower:
            embedding[i] = 1

    # Special flags
    align_flag = any(cue in nlp_lower for cue in ['align', 'matching', 'in line with']) and 'room' not in nlp_lower
    corner_flag = 'corner' in nlp_lower
    multi_object_flag = is_multi_object(nlp_input)

    embedding[-3] = 1 if align_flag else 0
    embedding[-2] = 1 if corner_flag else 0
    embedding[-1] = 1 if multi_object_flag else 0
    
    return embedding

# Build model (for reference, not used unless rebuilding)
def build_model():
    bert_model = TFBertModel.from_pretrained('bert-base-uncased')
    input_ids = tf.keras.layers.Input(shape=(50,), dtype=tf.int32, name='input_ids')
    attention_mask = tf.keras.layers.Input(shape=(50,), dtype=tf.int32, name='attention_mask')
    keyword_input = tf.keras.layers.Input(shape=(len(keywords) + 3,), dtype=tf.float32, name='keyword_embedding')

    bert_outputs = bert_model(input_ids, attention_mask=attention_mask)[0]
    pooled_output = bert_outputs[:, 0, :]  # [CLS] token
    combined = tf.keras.layers.Concatenate()([pooled_output, keyword_input])
    dense = tf.keras.layers.Dense(128, activation='relu')(combined)
    dropout = tf.keras.layers.Dropout(0.3)(dense)
    output = tf.keras.layers.Dense(len(command_types), activation='softmax')(dropout)

    model = tf.keras.Model(inputs=[input_ids, attention_mask, keyword_input], outputs=output)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=2e-5),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

# Predict DSL command type with post-processing
def predict_dsl(nlp_input, model, tokenizer):
    encoding = tokenizer([nlp_input], padding='max_length', truncation=True, max_length=50, return_tensors='tf')
    keyword_emb = np.array([create_keyword_embedding(nlp_input)])
    inputs = {
        'input_ids': encoding['input_ids'],
        'attention_mask': encoding['attention_mask'],
        'keyword_embedding': keyword_emb
    }
    logits = model(inputs)
    command_label = np.argmax(logits, axis=1)[0]
    command_type = label_to_command[command_label]
    # Post-processing rule
    if command_type == 'place_relative_multi' and not is_multi_object(nlp_input):
        command_type = 'place_relative'
    return command_type

# Main execution
if __name__ == "__main__":
    # Unzip the model weights
    zip_path = '/content/my_command_classifier_model.zip'  # Path to the ZIP file
    extract_path = '/content/my_command_classifier_model'  # Directory to extract to

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    # Verify extraction
    print("Extracted files:", os.listdir(extract_path))

    # Load tokenizer and model
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = tf.keras.models.load_model(
        extract_path,  # Load from the unzipped directory
        custom_objects={'TFBertModel': TFBertModel}
    )

    