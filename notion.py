#!/usr/bin/env python3
# fix links in notion.so export
#
# Copyright (C) 2023 Robert Wallis, All Rights Reserved.

import csv
import os
import re


MARKDOWN_LINK_PATTERN = re.compile('\[([^\]]+)\]\(([^\]]+)\)')
URL_MD5_PATTERN = re.compile('%20[a-fA-F0-9]{32}')
MD5_PATTERN = re.compile('\s*[a-fA-F0-9]{32}')


def main():
    walk_links('.')


def walk_links(rootpath: str):
    for (rootpath, dirs, files) in os.walk(rootpath):
        for filename in files:
            if '.md' == filename[-3:]:
                remove_md5_from_filename_and_markdown_links(rootpath, filename)
            if '.csv' == filename[-4:]:
                migrate_notion_table_to_obsidian_kanban(rootpath, filename)
        for dirname in dirs:
            walk_links(dirname)


def remove_md5_from_filename_and_markdown_links(rootpath: str, filename: str):
    filename = os.path.join(rootpath, filename)
    cleaned = remove_md5_from_filename(filename)
    filename_out = f"{cleaned}.out"
    if filename == cleaned:
        print(filename)
    else:
        cleaned_path = remove_md5_from_filename(rootpath)
        if cleaned_path != rootpath:
            print(f"mkdir {cleaned_path}")
            os.makedirs(cleaned_path, exist_ok=True)

    with open(filename) as file, open(filename_out, mode='w') as file_out:
        for line in file:
            matches = MARKDOWN_LINK_PATTERN.findall(line)
            for title, url in matches:
                url2 = remove_md5_from_url(url)
                if len(url2) and url != url2:
                    print(f" title: {title}")
                    print(f"    url1: {url}")
                    print(f"    url2: {url2}")
                    line = line.replace(url, url2)
            file_out.write(line)

    os.rename(filename_out, cleaned)


def remove_md5_from_url(url: str):
    """Removes the md5 hash from a url.
    >>> remove_md5_from_url('https://example.com/123%20aAbBcCdDeEfF00112233445566778899.md')
    'https://example.com/123.md'
    """
    matches = URL_MD5_PATTERN.findall(url)
    for match in matches:
        url = url.replace(match, '')
    return url


def remove_md5_from_filename(filename: str):
    """Removes the md5 hash from a filename.
    >>> remove_md5_from_filename('123 aAbBcCdDeEfF00112233445566778899.md')
    '123.md'
    """
    for match in MD5_PATTERN.findall(filename):
        filename = filename.replace(match, '')
    return filename


def migrate_notion_table_to_obsidian_kanban(rootpath: str, filename: str):
    filename = os.path.join(rootpath, filename)
    cleaned = remove_md5_from_filename(filename)
    cleaned.replace('.csv', '.md')

    # open the csv
    records = records_from_csv(filename)
    if len(records) == 0:
        return
    first_record = records[0]
    statuses = statuses_from_csv(records)
    status_records = records_grouped_by_status(records)
    keys = list(first_record.keys())
    title_key = keys[0] if keys else 'Name'
    unknown_params = unknown_record_params(first_record, [title_key, 'Status', 'Tags'])

    # write the kanban file
    with open(cleaned, mode='w') as kanban:
        # this is the markdown header for the kanban
        kanban.write('---')
        kanban.write('\n')
        kanban.write('kanban-plugin: basic')
        kanban.write('\n')
        kanban.write('---')
        kanban.write('\n')

        for status in statuses:
            kanban.write(f'## {status}\n')
            kanban.write('\n')
            for record in status_records[status]:
                line = '- '
                if status == 'Done':
                    line += f'[x] {record[title_key]}'
                else:
                    line += f'[ ] {record[title_key]}'

                for param in unknown_params:
                    if len(record[param]):
                        line += f' {param}:{record[param]}'

                if 'Tags' in record:
                    line += f' #{record["Tags"]}'
                kanban.write(line)
                kanban.write('\n')
            kanban.write('\n\n')


def records_from_csv(filename: str):
    """Reads a csv file, and returns an array of dicts.
    >>> import tempfile
    >>> file_data = '\ufeffName,Status,Tags\\nWork on CSV Exporter,Doing,notion\\n'
    >>> temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
    >>> temp_file.write(file_data)
    52
    >>> temp_file.close()
    >>> records_from_csv(temp_file.name)
    [{'Name': 'Work on CSV Exporter', 'Status': 'Doing', 'Tags': 'notion'}]
    """
    records = []
    # encoding='utf-8-sig' avoids the bom unicode header
    with open(filename, encoding='utf-8-sig') as csvfile:
        for row in csv.DictReader(csvfile):
            records.append(row)
    return records


def statuses_from_csv(csv_data: list[dict], default_status='TODO'):
    """Returns a list of unique statuses from a csv file.
    csv_data is a list of dicts, each dict is a row in the csv file.
    >>> statuses_from_csv([{'Status': ''}, {'Status': 'Doing'}, {'Status': 'Done'}])
    ['', 'Doing', 'Done']
    """
    statuses = []
    for row in csv_data:
        if 'Status' in row and row['Status'] not in statuses:
            statuses.append(row['Status'])
    if len(statuses) == 0:
        statuses.append(default_status)
    return statuses


def records_grouped_by_status(csv_data: list[dict], default_status=''):
    """Returns a dict of lists of records grouped by status.
    csv_data is a list of dicts, each dict is a row in the csv file.
    >>> records_grouped_by_status([{'Status': ''}, {'Status': 'Doing'}, {'Status': 'Done'}])
    {'': [{'Status': ''}], 'Doing': [{'Status': 'Doing'}], 'Done': [{'Status': 'Done'}]}
    """
    result = {}
    for row in csv_data:
        status = row['Status'] if 'Status' in row else default_status
        result.setdefault(status, []).append(row)
    return result


def unknown_record_params(record: dict, known_params: list[str]):
    """Returns a list of unknown parameters from a record.
    record is a dict, each key is a column in the csv file.
    >>> unknown_record_params({'Name': 'Work on CSV Exporter', 'Status': 'Doing', 'Tags': 'notion'}, ['Name', 'Status', 'Tags'])
    []
    """
    result = []
    for key in record.keys():
        if key not in known_params:
            result.append(key)
    return result


if __name__ == '__main__':
    main()

