import xml.etree.ElementTree as ET
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Copy specified element values from vanilla XML to types XML.')
parser.add_argument('element', type=str, help='The XML element to copy (e.g., lifetime)')
parser.add_argument('src_file', type=str, help='The source XML file path')
parser.add_argument('target_file', type=str, help='The target XML file path')
args = parser.parse_args()

element_to_copy = args.element
vanilla_file_path = args.src_file
types_file_path = args.target_file

# Parse the XML files
vanilla_tree = ET.parse(vanilla_file_path)
vanilla_root = vanilla_tree.getroot()

types_tree = ET.parse(types_file_path)
types_root = types_tree.getroot()

# Create a dictionary to store element values from vanilla file
element_dict = {}
for type_elem in vanilla_root.findall('type'):
    name = type_elem.get('name')
    element = type_elem.find(element_to_copy)
    if name and element is not None:
        element_dict[name] = element.text

# Update element values in types file
for type_elem in types_root.findall('type'):
    name = type_elem.get('name')
    if name in element_dict:
        element = type_elem.find(element_to_copy)
        if element is not None:
            element.text = element_dict[name]
        else:
            new_element = ET.SubElement(type_elem, element_to_copy)
            new_element.text = element_dict[name]

# Write the updated types file
types_tree.write(types_file_path)
