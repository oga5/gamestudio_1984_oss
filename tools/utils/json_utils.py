import re

def parse_value(val_str):
    """Parse string value to int, float, boolean, null or keep as string."""
    if val_str.lower() == 'true':
        return True
    if val_str.lower() == 'false':
        return False
    if val_str.lower() == 'null':
        return None
    try:
        return int(val_str)
    except ValueError:
        try:
            return float(val_str)
        except ValueError:
            # Remove quotes if present
            if (val_str.startswith('"') and val_str.endswith('"')) or \
               (val_str.startswith("'") and val_str.endswith("'")):
                return val_str[1:-1]
            return val_str

def split_selector(selector):
    """Split selector string by dot, respecting brackets."""
    parts = []
    current = []
    depth = 0
    
    for char in selector:
        if char == '.' and depth == 0:
            if current:
                parts.append(''.join(current))
                current = []
        else:
            if char == '[':
                depth += 1
            elif char == ']':
                depth -= 1
            current.append(char)
            
    if current:
        parts.append(''.join(current))
        
    return parts

def parse_segment(segment):
    """
    Parse a selector segment.
    Returns a dict with type and details.
    Types: 'dict_key', 'list_index', 'list_search'
    """
    match = re.match(r'^(.*?)\[(.*?)\]$', segment)
    if match:
        key = match.group(1)
        condition = match.group(2)
        
        info = {
            'key': key if key else None,
            'condition': condition
        }
        
        if '=' in condition:
            k, v = condition.split('=', 1)
            info['search_key'] = k.strip()
            info['search_value'] = parse_value(v.strip())
            info['type'] = 'list_search'
        else:
            try:
                info['index'] = int(condition)
                info['type'] = 'list_index'
            except ValueError:
                info['type'] = 'unknown'
        
        return info
    else:
        return {
            'type': 'dict_key',
            'key': segment
        }

def traverse_step(current, segment_info):
    """
    Move one step deeper into the JSON structure based on segment info.
    Returns the next object or None.
    """
    # Key access first (if dict key is present, e.g. "assets[...]")
    if segment_info['key']:
        if isinstance(current, dict):
            current = current.get(segment_info['key'])
        else:
            return None
            
    if current is None:
        return None

    # List access (if brackets were present)
    if 'type' in segment_info and segment_info['type'] in ['list_index', 'list_search']:
        if not isinstance(current, list):
            return None
            
        if segment_info['type'] == 'list_index':
            idx = segment_info['index']
            if 0 <= idx < len(current):
                return current[idx]
            return None
            
        elif segment_info['type'] == 'list_search':
            search_key = segment_info['search_key']
            search_val = segment_info['search_value']
            for item in current:
                if isinstance(item, dict) and item.get(search_key) == search_val:
                    return item
            return None
            
    return current
