#!/usr/bin/env python3

import gzip
import sys
import uuid
from dataclasses import dataclass
from xml.etree import ElementTree


@dataclass
class GnuCashFile:
    root: ElementTree.Element
    book: ElementTree.Element
    namespaces: dict


def extract_namespaces(filename: str) -> dict:
    ns = []

    with gzip.open(filename) as f:
        for _, elem in ElementTree.iterparse(f, ["start-ns"]):
            ns.append(elem)

    return dict(ns)


def load_gnucash_file(filename: str):
    ns = extract_namespaces(filename)

    for (prefix, uri) in ns.items():
        ElementTree.register_namespace(prefix, uri)

    with gzip.open(filename) as f:
        tree = ElementTree.parse(f)

    root = tree.getroot()
    book = root.find("gnc:book", ns)
    return GnuCashFile(root=root, book=book, namespaces=ns)


def remove_transactions(gnu_cash_file: GnuCashFile):
    ns = gnu_cash_file.namespaces
    book = gnu_cash_file.book

    # remove all transactions
    tx_count = 0
    for tx_node in book.findall("gnc:transaction", ns):
        book.remove(tx_node)
        tx_count += 1
    print("Removed %d transactions." % tx_count)
    # reset transaction count
    tx_count_reset = False
    for cnt_node in book.findall("gnc:count-data", ns):
        if cnt_node.get("{{{cd}}}type".format(**ns)) == "transaction":
            print("Resetting transaction count.")
            tx_count_reset = True
            cnt_node.text = "0"
    if not tx_count_reset:
        print("ERROR: could not reset the transaction counter.")


def insert_new_uuid(gnu_cash_file: GnuCashFile):
    ns = gnu_cash_file.namespaces
    book = gnu_cash_file.book

    # generate a new UUID for the file
    id_node = book.find("book:id", ns)
    if id_node.get("type") == "guid":
        print("Setting new UUID for book.")
        id_node.text = uuid.uuid4().hex
    else:
        print("ERROR: could not assing a new UUID for book.")


def disable_scheduled_transactions(gnu_cash_file: GnuCashFile):
    ns = gnu_cash_file.namespaces
    book = gnu_cash_file.book

    # Disable all scheduled transactions
    schedule_cnt = 0
    for n in book.findall("./gnc:schedxaction/sx:enabled", ns):
        n.text = "n"
        schedule_cnt += 1
    print("Disabled %d schedules." % schedule_cnt)


def store_book(gnu_cash_file: GnuCashFile, output_file: str):
    root = gnu_cash_file.root

    with open(output_file + ".xml", mode="wb") as xml_file:
        ElementTree.ElementTree(root).write(xml_file, encoding="utf-8", xml_declaration=True)

    with gzip.open(output_file + ".gnucash", mode="wb", compresslevel=9) as gzip_file:
        ElementTree.ElementTree(root).write(gzip_file, encoding="utf-8", xml_declaration=True)


if __name__ == '__main__':
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    print("Input: %s" % input_file)
    print("Output: %s" % output_file)

    gnu_cash_file = load_gnucash_file(input_file)
    remove_transactions(gnu_cash_file)
    insert_new_uuid(gnu_cash_file)
    disable_scheduled_transactions(gnu_cash_file)

    store_book(gnu_cash_file, output_file)
