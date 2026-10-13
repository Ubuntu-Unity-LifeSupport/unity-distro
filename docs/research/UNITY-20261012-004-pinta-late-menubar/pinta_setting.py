#!/usr/bin/python3
"""pinta_setting.py FILE NAME True|False - set one boolean in Pinta's settings.xml (~/.config/Pinta/settings.xml,
the format of Pinta.Core/Managers/SettingsManager.cs: <settings><setting name=".." type="System.Boolean">True
</setting>...), creating the file if needed, and print the result."""
import os
import sys
import xml.etree.ElementTree as ET

path, name, value = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.dirname(path), exist_ok=True)
try:
    tree = ET.parse(path)
    root = tree.getroot()
except (OSError, ET.ParseError):
    root = ET.Element('settings')
    tree = ET.ElementTree(root)
node = next((s for s in root.findall('setting') if s.get('name') == name), None)
if node is None:
    node = ET.SubElement(root, 'setting', {'name': name, 'type': 'System.Boolean'})
node.set('type', 'System.Boolean')
node.text = value
tree.write(path, encoding='utf-8', xml_declaration=True)
print(f'  pinta setting {name} = {value} in {path}')
