from logging import info
from pathlib import Path

from lxml.etree import parse
from lxml.etree import XPath
from regex import compile
from regex import IGNORECASE
from regex import MULTILINE

from legal_nlp_pipeline.fetch_xml_rulings import NAMESPACE_PREFIX_MAP

ENCODING = 'utf-8'

ALPINO_SPECIAL_CHAR_PERCENT = compile(pattern=r'%+', flags=MULTILINE)
ALPINO_SPECIAL_CHARS = compile(pattern=r'[\|\[\]]+')
DASH_LIKES = compile(
    pattern=r'[–—]+', flags=MULTILINE)  # TODO: \p{Dash_Punctuation}
ELLIPSIS = compile(pattern=r'\((:?\.\.\.|\-\))')
CENSORED_IDENTIFIER = compile(pattern=r'\[\s+\]', flags=MULTILINE)
ODD_CHARS_REX = compile(pattern=r'[¬]+', flags=MULTILINE)
# DOUBLE_QUOTES = compile(pattern=r'[“”]+')
# SINGLE_QUOTES = compile(pattern=r'[‘’]+')
CENSORED_NAAMX = compile(pattern=r'\[?[Nn]aam\s*([0-9]*)\]?')
NER_PITFALL_MRS = compile(pattern=r' [Mm]rs\.')
WHITESPACE_PUNCTUATION_REX = compile(
    pattern=r'\s*([;:,]+)\s+', flags=MULTILINE)
# WHITESPACE_REX = compile(pattern=r'(?:[^\S\n]{2,}|[\xa0]+)', MULTILINE)
WHITESPACE_REX = compile(pattern=r'(?:\p{Zs}+)', flags=MULTILINE)
# WIJZERS = compile(pattern=r'(?:Aldus gewezen door|Dit vonnis is gewezen
# door|Deze beslissing is genomen door|'
#                   r'Deze beslissing is gegeven door|Deze beslissing is
# gegeven op|Aldus gegeven door|'
#                   r'Deze beschikking is gegeven door|Dit arrest is gewezen
#  door|Deze beschikking is gewezen door|'
#                   r'Deze beschikking is gegeven in|Aldus gedaan in'
#                   r'Aldus gedaan door).*', MULTILINE | DOTALL | IGNORECASE)
# WRAKING_PARTIES = \
#    compile(r'\b(:?appellant|appellante|geappelleerde|geïntimeerde
# |verzoeker|verzoekster|verweerder|verweerster)\b',
#            IGNORECASE)
RULES = compile(
    pattern=r'(:?[_\-–—=]{3,}(:?\s?[_\-–—=])*)+')  # Horizontal text rules
# TODO: add newline anchors?
LISTS = compile(
    pattern=r'((?<=[:;\.])\s+(?:(?:\(?[a-z]\))|[•\-\*])[^;]+)',
    flags=MULTILINE)
EXPLODED_WORDS_1 = compile(pattern=r'B E S L I S\s*S I N G', flags=IGNORECASE)
EXPLODED_WORDS_2 = compile(pattern=r'U I T S P R A A K', flags=IGNORECASE)
EXPLODED_WORDS_3 = compile(
    pattern=r'P R O C E S \- V E R B A A L', flags=IGNORECASE)
PROCENT = compile(pattern=r'([0-9]{1,3})\s*(:?procent|%)')


def clean(ruling_text: str):
    # TODO: line symbols
    # SINGLE_QUOTES.sub(repl="'", string=
    # DOUBLE_QUOTES.sub(repl='"', string=
    # @formatter:off
    return \
        WHITESPACE_REX.sub(repl=r' ', string=
        DASH_LIKES.sub(repl=r'-', string=
        RULES.sub(repl=r'\n', string=
        ELLIPSIS.sub(repl=r'', string=
        NER_PITFALL_MRS.sub(repl=r' mr.', string=
        ALPINO_SPECIAL_CHAR_PERCENT.sub(repl=r'procent', string=
        ALPINO_SPECIAL_CHARS.sub(repl=r'', string=
        CENSORED_IDENTIFIER.sub(repl=r' X', string=
        CENSORED_NAAMX.sub(repl=r'Naam \1', string=
        LISTS.sub(repl=r'\n\1', string=
        PROCENT.sub(repl=r'\1 %', string=
        WHITESPACE_PUNCTUATION_REX.sub(repl=r'\1 ', string=
        EXPLODED_WORDS_1.sub(repl=r'Beslissing', string=
        EXPLODED_WORDS_2.sub(repl=r'Uitspraak', string=
        EXPLODED_WORDS_3.sub(repl=r'Proces-verbaal', string=
        WHITESPACE_REX.sub(repl=r' ', string=
        ODD_CHARS_REX.sub(repl=r'', string=ruling_text)))))))))))))))))
    # @formatter:on


def extract_wraking_text(ruling_tree):
    # Do something to preserve existent sentence/line structure (titles e.g.)
    xpath_strs = ('/open-rechtspraak/rvr:uitspraak//text()',
                  )  # /open-rechtspraak/rvr:uitspraak//rvr:para |
    # xpath_strs = ('normalize-space(/open-rechtspraak/rvr:uitspraak)',)
    xpaths = (XPath(
        xpath_str, namespaces=NAMESPACE_PREFIX_MAP)
              for xpath_str in xpath_strs)

    emphasis_el_name = '{{{rvr:s}}}emphasis'.format(
        rvr=NAMESPACE_PREFIX_MAP['rvr'])
    title_element_name = '{{{rvr:s}}}title'.format(
        rvr=NAMESPACE_PREFIX_MAP['rvr'])
    nr_element_name = '{{{rvr:s}}}nr'.format(rvr=NAMESPACE_PREFIX_MAP['rvr'])
    concatd_str = ''
    last_len = 0
    for xpath in xpaths:
        for text_node in xpath(ruling_tree):
            stripped_text = text_node.strip()
            if stripped_text != '':
                parent_element = text_node.getparent()
                par_el_name = parent_element.tag
                grandpar_el_text = parent_element.getparent().text
                if grandpar_el_text is not None:
                    grandpar_el_text = grandpar_el_text.strip()
                else:
                    grandpar_el_text = ''
                stripped_text_len = len(stripped_text)

                if par_el_name == title_element_name or par_el_name == \
                        nr_element_name:
                    concatd_str = concatd_str + '\n' + \
                                  stripped_text + '\n'
                    # TODO: use StringIO
                    # items = tuple(' '.join(xpath(ruling_tree) if .strip()
                    # != '\n' else '')
                elif (par_el_name == emphasis_el_name and grandpar_el_text
                    != '') or concatd_str.endswith(',') or concatd_str.endswith(':') or \
                                stripped_text_len > 70 or (
                                last_len > 70 and stripped_text.endswith(
                            ' van')):
                    concatd_str = concatd_str + \
                                  stripped_text + ' '
                    # TODO: redundant
                else:
                    concatd_str = concatd_str + \
                                  stripped_text + '\n'

                last_len = stripped_text_len
    items = concatd_str,  # TODO: stop using tuple

    if len(items) > 0:
        if len(items) <= 1:
            text = clean(items[0])
            return text
        elif len(items) > 1:
            assert False
    else:
        return None


def extract_wraking_texts(xml_rulings_dir_path: Path, target_dir_path: Path,
                          out_suffix: str, work_distribution):
    info('Extracting wraking texts ...')
    xml_ruling_files = (xml_rulings_dir_path.joinpath(ecli).with_suffix('.xml')
                        for ecli in work_distribution)
    for xml_ruling_file_path in xml_ruling_files:
        if xml_ruling_file_path.is_file() and xml_ruling_file_path.stat(
        ).st_size != 0:
            ruling_tree = parse(str(xml_ruling_file_path))
            text_file_path = target_dir_path.joinpath(
                xml_ruling_file_path.name).with_suffix(out_suffix)
            if not text_file_path.is_file() or text_file_path.stat(
            ).st_size == 0:
                text = extract_wraking_text(ruling_tree)
                if text is not None:
                    with text_file_path.open(
                            mode='wt', encoding=ENCODING) as text_file:
                        text_file.write(text)
                status = 'OK' if text is not None else '--'
                info("Extracted wraking text to '{text_file_path}' => "
                     "txt: {status:s}".format(
                         text_file_path=text_file_path, status=status))
        else:
            raise RuntimeError(
                "XML ruling file '{xml_ruling_file_path}' has size zero or "
                "does not exist. ".format(
                    xml_ruling_file_path=xml_ruling_file_path))
    info("Extracted wraking texts to '{target_dir_path}'. ".format(
        target_dir_path=target_dir_path))
