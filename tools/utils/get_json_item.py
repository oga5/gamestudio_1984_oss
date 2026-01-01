import json
import sys
import os
import argparse
try:
    from .json_utils import split_selector, parse_segment, traverse_step
except ImportError:
    from json_utils import split_selector, parse_segment, traverse_step

def get_json_item(data, selector):
    """
    Traverse JSON data using a selector string.
    """
    parts = split_selector(selector)
    current = data
    
    for part in parts:
        info = parse_segment(part)
        current = traverse_step(current, info)
        if current is None:
            return None
                
    return current

def main():
    parser = argparse.ArgumentParser(description='Get item from JSON file using selector.')
    parser.add_argument('file_path', help='Path to the JSON file')
    parser.add_argument('selector', help='Selector string (e.g. assets[id=30])')
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
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = get_json_item(data, args.selector)
        
        if result is not None:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("Item not found")
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
