# from collections import Iterable
from pathlib import Path

from legal_nlp_pipeline.extract_rulings_texts_wraking import clean
from legal_nlp_pipeline.extract_rulings_texts_wraking import WIJZERS
from legal_nlp_pipeline.fetch_xml_rulings import NAMESPACE_PREFIX_MAP

ENCODING = 'utf-8'

# ALPINO_SPECIAL_CHARS includes [], which coincides with the censored named entity marking [...] in the original data.


def filter_out_wijzers(uitspraak_text: str):
    return WIJZERS.sub(repl='', string=uitspraak_text)


def select_tokenized_files(tokenized_files_dir_path: Path, target_dir_path:
                           Path, work_distribution):
    from logging import info

    tokenized_files = (tokenized_files_dir_path.joinpath(ecli + '.xml.txt.tok')
                       for ecli in work_distribution)

    for tokenized_file_path in tokenized_files:
        selected_file_path = target_dir_path.joinpath(
            tokenized_file_path.name).with_suffix('.sel')
        if not selected_file_path.exists() or selected_file_path.stat(
        ).st_size == 0:
            with tokenized_file_path.open(
                    mode='rt', encoding=ENCODING) as tokenized_file:
                with selected_file_path.open(
                        mode='wt', encoding=ENCODING) as selected_file:
                    # TODO: preselection? select_sentences_with_wraking_party_mentions
                    selected_file.write(
                        tokenized_file.read(), encoding=ENCODING)
                    info("Selected to '{selected_file_path}'.".format(
                        selected_file_path=selected_file_path))


def determine_zittingsplaats(ruling_tree):
    from lxml.etree import XPath

    xpaths = (XPath(
        '/open-rechtspraak/rdf:RDF/rdf:Description/dcterms:spatial[@rdfs:label]/text()',
        namespaces=NAMESPACE_PREFIX_MAP), )
    items = tuple('\n'.join(xpath(ruling_tree)) for xpath in xpaths)

    if len(items) == 1:
        return items[0]
    else:
        return None


def extract_uitspraak(ruling_tree):
    from lxml.etree import XPath

    xpath_strs = [
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:*/text()[contains(., 'DE UITSPRAAK')]/"
        "ancestor::rvr:section/descendant-or-self::text() | "
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:*/text()[contains(., 'DE UITSPRAAK')]/"
        "ancestor::rvr:section/following-sibling::rvr:section/descendant-or-self::text()",
        '/open-rechtspraak/rvr:uitspraak/rvr:section[@role="beslissing"][last()]/descendant-or-self::text()',
        "/open-rechtspraak/rvr:uitspraak/rvr:section/rvr:title/text()[contains(., 'eslissing')][last()]//"
        "ancestor::rvr:section/descendant-or-self::text()"
    ]

    xpaths = (XPath(
        xpath_str, namespaces=NAMESPACE_PREFIX_MAP)
              for xpath_str in xpath_strs)
    items = tuple('\n'.join(xpath(ruling_tree)) for xpath in xpaths)

    if len(items) >= 1:
        if len(items) <= 3:
            return filter_out_wijzers(
                clean(items[0]))  # TODO: if != '' ; precedence of XPaths
        elif len(items) > 3:
            assert False
    else:
        return None


def extract_tenlastelegging(ruling_tree):
    from lxml.etree import XPath

    xpaths = (XPath(
        "/open-rechtspraak/rvr:uitspraak/rvr:section/rvr:title/"
        "descendant-or-self::*/text()[contains(., 'tenlastelegging')]/ancestor::rvr:section"
        "//*[not(local-name()='nr')]/text()",
        namespaces=NAMESPACE_PREFIX_MAP), )

    items = tuple('\n'.join(xpath(ruling_tree)) for xpath in xpaths)

    if len(items) == 1:
        return clean(items[0])
    else:
        return None


def extract_standpunt_ovj(ruling_tree):
    from lxml.etree import XPath

    xpath_strs = (
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:parablock/rvr:para/"
        "descendant-or-self::*[contains(text(), 'standpunt van de officier van justitie') "
        "or contains(text(), 'standpunt van de officieren van justitie') "
        "or contains(text(), 'standpunt van het Openbaar Ministerie') "
        "or contains(text(), 'standpunt van het openbaar ministerie')]/"
        "ancestor::rvr:para/following-sibling::rvr:para/text() | "
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:para/rvr:emphasis/"
        "descendant-or-self::*/text()[contains(., ' eis van de officier van justitie') or "
        "contains(., ' eis van de officieren van justitie')]/"
        "ancestor::rvr:para/following-sibling::rvr:para/text()",
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:paragroup/"
        "descendant-or-self::*[contains(text(), 'standpunt van de officier van justitie') "
        "or contains(text(), 'standpunt van de officieren van justitie') "
        "or contains(text(), 'standpunt van het Openbaar Ministerie') "
        "or contains(text(), 'standpunt van het openbaar ministerie')]/"
        "parent::*/descendant::rvr:parablock/descendant::*/text()",
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:para/"  # TODO: remove, strafoplegging != bewijs
        "rvr:emphasis[text()='De vordering van de officier van justitie' or "
        "text()='De vordering van de officieren van justitie']/"
        "ancestor::rvr:para/following-sibling::rvr:*/text()"  # ,
        # "/open-rechtspraak/rvr:uitspraak/rvr:section/rvr:parablock/rvr:para/rvr:emphasis"
        , )

    xpaths = (XPath(
        xpath_str, namespaces=NAMESPACE_PREFIX_MAP)
              for xpath_str in xpath_strs)
    items = tuple('\n'.join(xpath(ruling_tree)) for xpath in xpaths)

    if len(items) > 0:
        if len(items) <= 2:
            return clean(items[0])
        elif len(items) > 2:
            assert False
    else:
        return None


def extract_standpunt_adv(ruling_tree):
    from lxml.etree import XPath

    xpath_strs = [
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:parablock/rvr:para/"
        "descendant-or-self::*[contains(text(), 'standpunt van de verdediging')]/"
        "ancestor::rvr:para/following-sibling::rvr:para/text()",
        "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:paragroup/"
        "descendant-or-self::*[contains(text(), 'standpunt van de Verdediging') "  # TODO: unneeded
        "or contains(text(), 'standpunt van de verdediging')"
        "or contains(text(), 'standpunt van verdediging')]/"  # TODO: unneeded
        "parent::*/descendant::rvr:parablock/descendant::*/text()"
    ]  # ,
    # "/open-rechtspraak/rvr:uitspraak/rvr:section//rvr:para/"
    # "rvr:emphasis[text()='Het standpunt van de verdediging']/"
    # "ancestor::rvr:para/following-sibling::rvr:*/text()"]

    xpaths = (XPath(
        xpath_str, namespaces=NAMESPACE_PREFIX_MAP)
              for xpath_str in xpath_strs)
    items = tuple('\n'.join(xpath(ruling_tree)) for xpath in xpaths)

    if len(items) == 1:
        return clean(items[0])
    elif len(items) > 1:
        assert False
    else:
        return None


def extract_composite_ruling(ruling_tree):
    tenlastelegging = extract_single_tenlastelegging(
        extract_tenlastelegging(ruling_tree))
    standpunt_adv = extract_standpunt_adv(ruling_tree)
    standpunt_ovj = extract_standpunt_ovj(ruling_tree)
    beslissing = extract_uitspraak(ruling_tree)

    return tenlastelegging, standpunt_adv, standpunt_ovj, beslissing


def extract_single_tenlastelegging(tenlastelegging: str):
    if tenlastelegging is not None:
        from re import compile, MULTILINE

        _, _, tenlastelegging = tenlastelegging.partition('tenlastelegging')

        numeral = ".{0,10}\d+[:\.]?"
        parketnummer = "[Pp]arketnummer .{0,20}"

        rex = compile(
            r"^(" + numeral + r"|" + numeral + r"\n" + parketnummer + r"|" +
            parketnummer + r")$",
            flags=MULTILINE)
        matches = rex.findall(tenlastelegging)

        # "feit 1"
        # #
        # ten aanzien van parketnummer 09/842168-13:
        # 1.

        if matches is not None and len(matches) > 1:
            return None
    # TODO: filter empty lines
    return tenlastelegging


def extract_composite_rulings(xml_ruling_files, target_dir_path: Path):
    from logging import debug, info
    from lxml.etree import parse

    almost_count = 0

    for ruling_file_path in xml_ruling_files:
        ruling_tree = parse(str(ruling_file_path))  # TODO: xml_ruling_files ??
        tenlastelegging, standpunt_adv, standpunt_ovj, beslissing = extract_composite_ruling(
            ruling_tree)
        # ruling_file_path == 'docs/ECLI:NL:RBOBR:2013:5003.xml' and beslissing is None

        if tenlastelegging is not None and standpunt_adv is not None and \
                        standpunt_ovj is not None and beslissing is not None:
            target_file_path = target_dir_path.joinpath(ruling_file_path.name)
            # symlink(ruling_file_path, target_file_path)

            with target_file_path.with_suffix('.tlg.txt').open(
                    mode='wt', encoding=ENCODING) as target_file:
                target_file.write(tenlastelegging)

            with target_file_path.with_suffix('.adv.txt').open(
                    mode='wt', encoding=ENCODING) as target_file:
                target_file.write(standpunt_adv)

            with target_file_path.with_suffix('.ovj.txt').open(
                    mode='wt', encoding=ENCODING) as target_file:
                target_file.write(standpunt_ovj)

            with target_file_path.with_suffix('.bsl.txt').open(
                    mode='wt', encoding=ENCODING) as target_file:
                target_file.write(beslissing)
                # 1
        else:
            extraction_status = "tlg: {0}  sadv: {1}  sovj: {2}  bs: {3}".format(
                'OK' if tenlastelegging is not None else '--', 'OK'
                if standpunt_adv is not None else '--', 'OK'
                if standpunt_ovj is not None else '--', 'OK'
                if beslissing is not None else '--')
            info(extraction_status)
            if tenlastelegging is not None and extraction_status.count(
                    "OK") == 3:
                almost_count += 1
                # print(1)
                # 1  # tenlastelegging is not None and extraction_status.count("OK") == 3
    debug("Almost: {0:d}. ".format(almost_count))
