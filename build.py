#!/usr/bin/env python

import argparse
from datetime import datetime
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import yaml


def indent(elem, level=0):
    '''
    Nicely formats output xml with newlines and spaces
    https://stackoverflow.com/a/33956544
    '''
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def create_addon_xml(config, source, py_version):
    '''
    Create addon.xml from template file
    '''
    # Load template file
    with open('{}/.config/template.xml'.format(source), 'r') as f:
        tree = ET.parse(f)
        root = tree.getroot()

    # Populate dependencies in template
    dependencies = config['dependencies'].get(py_version)
    for dep in dependencies:
        ET.SubElement(root.find('requires'), 'import', attrib=dep)

    # Populate version string
    addon_version = config.get('version')
    root.attrib['version'] = '{}+{}'.format(addon_version, py_version)

    # Populate Changelog
    date = datetime.today().strftime('%Y-%m-%d')
    changelog = config.get('changelog')
    for section in root.findall('extension'):
        news = section.findall('news')
        if news:
            news[0].text = 'v{} ({}):\n{}'.format(addon_version, date, changelog)

    # Format xml tree
    indent(root)

    # Write addon.xml
    tree.write('{}/addon.xml'.format(source), encoding='utf-8', xml_declaration=True)


def zip_files(py_version, source, target):
    '''
    Create installable addon zip archive
    '''
    archive_name = 'plugin.video.jellyfin+{}.zip'.format(py_version)

    with zipfile.ZipFile('{}/{}'.format(target, archive_name), 'w') as z:
        for root, dirs, files in os.walk(args.source):
            for filename in files:
                if 'plugin.video.jellyfin' not in filename and 'pyo' not in filename:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.join('plugin.video.jellyfin', os.path.relpath(file_path, source))
                    z.write(file_path, relative_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build flags:')
    parser.add_argument(
        '--version',
        type=str,
        choices=('py2', 'py3'),
        default='py3')

    parser.add_argument(
        '--source',
        type=Path,
        default=Path(__file__).absolute().parent)

    parser.add_argument(
        '--target',
        type=Path,
        default=Path(__file__).absolute().parent)

    args = parser.parse_args()

    # Load config file
    config_path = os.path.join(args.source, 'release.yaml')
    with open(config_path, 'r') as fh:
        config = yaml.safe_load(fh)

    #py_version = 'py{}'.format(args.version)

    create_addon_xml(config, args.source, args.version)

    zip_files(args.version, args.source, args.target)
