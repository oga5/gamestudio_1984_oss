import json
import sys
import os
import argparse
try:
    from .json_utils import split_selector, parse_segment, traverse_step
except ImportError:
    from json_utils import split_selector, parse_segment, traverse_step

def edit_json_item(data, selector, new_value):
    """
    Edit or append an item in JSON data using a selector string.
    """
    parts = split_selector(selector)
    if not parts:
        raise ValueError("Empty selector")

    parent = data
    path_parts = parts[:-1]
    target_part = parts[-1]

    # Traverse to parent
    for part in path_parts:
        info = parse_segment(part)
        parent = traverse_step(parent, info)
        if parent is None:
            raise ValueError(f"Path not found: {part}")

    # Process target
    last_info = parse_segment(target_part)
    
    # 1. Handle Dictionary Key Access
    container = parent
    if last_info['key']:
        if not isinstance(container, dict):
            raise ValueError(f"Parent is not a dict for key: {last_info['key']}")
        
        # If no list access ([...]), simple dict update
        if 'type' not in last_info or last_info['type'] == 'dict_key':
            container[last_info['key']] = new_value
            return True
        
        # If list access follows, get the list
        container = container.get(last_info['key'])
        if container is None:
            # Create new list if it doesn't exist (and we are doing list operation)
            container = []
            parent[last_info['key']] = container

    # 2. Handle List Access
    if not isinstance(container, list):
        raise ValueError(f"Target is not a list: {target_part}")

    if last_info['type'] == 'list_search':
        search_key = last_info['search_key']
        search_val = last_info['search_value']
        found_idx = -1
        for i, item in enumerate(container):
            if isinstance(item, dict) and item.get(search_key) == search_val:
                found_idx = i
                break
        
        if found_idx >= 0:
            # Replace
            container[found_idx] = new_value
            print(f"Item replaced at index {found_idx}")
        else:
            # Append
            container.append(new_value)
            print("Item appended")
            
    elif last_info['type'] == 'list_index':
        idx = last_info['index']
        if 0 <= idx < len(container):
            container[idx] = new_value
            print(f"Item replaced at index {idx}")
        elif idx == len(container):
            container.append(new_value)
            print(f"Item appended at index {idx}")
        else:
            raise ValueError(f"Index out of range: {idx}")
    else:
        raise ValueError(f"Unknown selector type: {target_part}")

    return True

def main():
    parser = argparse.ArgumentParser(description='Edit item in JSON file using selector.')
    parser.add_argument('file_path', help='Path to the JSON file')
    parser.add_argument('selector', help='Selector string (e.g. assets[id=30])')
    parser.add_argument('new_value', help='New value as JSON string')
    parser.add_argument('--root_dir', help='Root directory to resolve file path')

    args = parser.parse_args()

    file_path = args.file_path
    if args.root_dir:
        if file_path.startswith("/"):
             file_path = file_path.lstrip("/")
        file_path = os.path.join(args.root_dir, file_path)

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        new_value = json.loads(args.new_value)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON for new value: {e}")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        edit_json_item(data, args.selector, new_value)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print("File updated successfully")
            
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
