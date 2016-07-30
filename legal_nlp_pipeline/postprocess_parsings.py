from collections import defaultdict
from collections import deque
from enum import IntEnum
from json import dump
from logging import debug
from logging import info
from logging import warning
from multiprocessing import Pool
from pathlib import Path
from subprocess import check_call

from lxml.etree import parse
from lxml.etree import XPath

ENCODING = 'utf-8'


class SentenceType(IntEnum):
    irrelevant = 0
    refused = 1
    upheld = 2
    without_cause = 3
    predictive_text = 4

# ECLI:NL:GHAMS:2013:4770
# TODO: ECLI:NL:GHAMS:2013:4770/195.xml is missing, is on IJsvogel
# TODO: reorder
upheld_xpath_spec = "/alpino_ds//node[(@cat='smain' or (@cat='sv1' and not(" \
                    "node[@rel='su']))) and " \
                    "node[@sense='wijs_toe' and @rel='hd' and @pt='ww' and " \
                    "@pvtijd='tgw']]"
# /alpino_ds//node[@sense='wijs_toe' and @rel='hd' and @pt='ww' and
# @pvtijd='tgw']"  (@pvtijd='tgw' or @wvorm='vd')
refused_xpath_spec = "/alpino_ds//node[(@cat='smain' or (@cat='sv1' and not(" \
                     "node[@rel='su']))) and " \
                     "node[@sense='wijs_af' and @rel='hd' and @pt='ww' and " \
                     "@pvtijd='tgw']]"
# refused_xpath_spec =
# "/alpino_ds//node[@sense='wijs_af' and @rel='hd' and @pt='ww' and (
# @pvtijd='tgw' or @wvorm='vd')]"
without_cause_xpath_spec = "/alpino_ds//node[(@cat='smain' or (@cat='sv1' " \
                           "and not(node[@rel='su']))) and " \
                           "node[@sense='niet_ontvankelijk'] and node[" \
                           "@rel='hd' and @pt='ww' and @sense='verklaar']]"
predictive_text_xpath_spec = "/alpino_ds//node[@cat='smain']"  # TODO:


def determine_sentence_type(xml_tree):
    if len(XPath(refused_xpath_spec)(xml_tree)) > 0:
        return SentenceType.refused
    elif len(XPath(upheld_xpath_spec)(xml_tree)) > 0:
        return SentenceType.upheld
    elif len(XPath(without_cause_xpath_spec)(xml_tree)) > 0:
        return SentenceType.without_cause
    elif len(XPath(predictive_text_xpath_spec)(xml_tree)) > 0:
        return SentenceType.predictive_text
    else:
        return SentenceType.irrelevant


def postprocess_parsed_file_directly(parsed_file_path: Path):
    if parsed_file_path.is_file() and parsed_file_path.stat().st_size != 0:
        try:
            xml_tree = parse(str(parsed_file_path))

            sentence_type = determine_sentence_type(xml_tree=xml_tree)
            ecli = parsed_file_path.parent.name
            sentence_index = int(parsed_file_path.stem)
        except:
            raise
        else:
            debug("Postprocessed parsed file {parsed_file_path}. ".format(
                parsed_file_path=parsed_file_path))
            return ecli, sentence_index, sentence_type
    else:
        warning(
            "Skipping parsed file to be postprocessed at '{parsed_file_path}'"
            ". ".format(parsed_file_path=parsed_file_path))

# TODO: reject rulings without any verdict


def postprocess_parsed_files_multiprocessing(
        parsed_dir_path: Path, target_dir_path: Path, n_cores: int, in_suffix:
        str, work_distribution):
    info('Postprocessing parsed files (multiprocessing) ... ')
    # TODO: consistency, parsing vs. parsed files.

    with Pool(processes=n_cores) as pool:
        futures = deque()

        for parsed_file_path in parsed_dir_path.glob('*/*.xml'):
            if parsed_file_path.is_file() and parsed_file_path.stat(
            ).st_size != 0:
                futures.append(
                    pool.apply_async(
                        func=postprocess_parsed_file_directly,
                        args=(parsed_file_path, )))
            else:
                raise RuntimeError(
                    "Postprocessed parsed file at '{parsed_file_path}' is '"
                    "'not a file or has zero size. ".format(
                        parsed_file_path=parsed_file_path))

        pool.close()

        postprocessing_dict = defaultdict(dict)
        for future in futures:
            val = future.get()
            # TODO: val redundant...

            ecli, sentence_index, sentence_type = val
            # TODO: efficiency
            if sentence_type is not SentenceType.irrelevant:
                postprocessing_dict[ecli][sentence_index] = sentence_type.value

        with target_dir_path.joinpath('sentence_types.json').open(
                mode='wt', encoding="ascii") as json_file:
            dump(
                dict(postprocessing_dict),
                json_file,
                sort_keys=True,
                indent=True)

        try:
            target_dir_path.joinpath('0').mkdir()
            target_dir_path.joinpath('1').mkdir()
        except FileExistsError:
            pass

        for ecli, sentences in postprocessing_dict.items():
            sentence_indices = sorted(sentences.keys(), reverse=True)
            new_sentence_indices = []
            document_label = None
            for sentence_index in sentence_indices:
                sentence_type = sentences[sentence_index]

                if document_label is None and sentence_type != \
                        SentenceType.predictive_text:
                    document_label = 0 if sentence_type == \
                                          SentenceType.upheld else 1
                    # TODO: only search at end
                else:
                    new_sentence_indices.append(sentence_index)

            if document_label is not None:
                document_file_path = target_dir_path.joinpath(
                    '{document_label:d}'.format(
                        document_label=document_label)).joinpath(
                            ecli).with_suffix('.doc')
                input_document_file_path = Path(
                    '/srv/data/legal_nlp_pipeline_1/11-6-2015/2_tokenized/{'
                    'ecli:s}.txt.tok'.format(
                        document_label=document_label, ecli=ecli))  # TODO:
                with document_file_path.open(
                        mode='wt', encoding=ENCODING) as output_document_file:
                    with input_document_file_path.open(
                            mode='rt',
                            encoding=ENCODING) as input_document_file:
                        lines_expr = ''
                        for new_sentence_index in new_sentence_indices:
                            lines_expr += '{0:d}p;'.format(new_sentence_index)

                        check_call(
                            ('sed',
                             '-n',
                             lines_expr, ),
                            stdin=input_document_file,
                            stdout=output_document_file)

    info("Performed postprocessing to '{target_dir_path}'. ".format(
        target_dir_path=target_dir_path))
