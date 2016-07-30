# from collections import Iterable
# from lxml.etree import XPath
from argparse import ArgumentParser
from itertools import chain
from logging import basicConfig, info, warning, INFO
from os import getpid
from pathlib import Path
from stat import S_ISGID, S_IRUSR, S_IWUSR, S_IXUSR, S_IRGRP, S_IXGRP, S_IROTH, S_IXOTH

from legal_nlp_pipeline.alpino_tokenize import alpino_tokenize_text_files
from legal_nlp_pipeline.extract_rulings_texts_wraking import extract_wraking_texts
from legal_nlp_pipeline.fetch_xml_rulings import fetch_and_process_eclis
from legal_nlp_pipeline.parse_rulings_texts import alpino_parse_tokenized_files_directly_multiprocessing
from legal_nlp_pipeline.postprocess_parsings import postprocess_parsed_files_multiprocessing

DIRECTORY_PERMISSIONS = S_ISGID | S_IRUSR | S_IWUSR | S_IXUSR | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH

# TODO: move into module


def determine_ecli(xml_ruling_file_path: Path):
    return xml_ruling_file_path.name.split('.')[0]


def distribute_work(args):
    from collections import defaultdict
    from itertools import chain
    from json import dump, load
    from logging import debug, info
    from random import choice

    info('Distributing work ... ')

    cluster_file_path = args.output_dir_path.joinpath(args.cluster_file_name)
    with cluster_file_path.open(mode='rt') as cluster_file:
        cluster = load(cluster_file)
        debug('Cluster: {cluster}'.format(cluster=cluster))

    xml_ruling_files_paths = args.xml_rulings_dir_path.glob('*.xml')

    eclis = (determine_ecli(xml_ruling_file_path)
             for xml_ruling_file_path in xml_ruling_files_paths)

    node_distribution = tuple(
        chain.from_iterable((node['name'] for _ in range(node['weight']))
                            for node in cluster))

    work_distribution = defaultdict(list)
    for ecli in eclis:
        work_distribution[choice(node_distribution)].append(ecli)
        # [for node in cluster] # TODO: efficiency?

    for node_id, node_jobs in work_distribution.items():
        work_distribution_file_path = args.output_dir_path.joinpath(
            str(node_id)).with_suffix('.json')
        with work_distribution_file_path.open(
                mode='wt') as work_distribution_file:
            dump(node_jobs, work_distribution_file)
            info(
                "Distributed {n_node_jobs:d} jobs to node {node_id}, as recorded at "
                "'{work_distribution_file_path}'. ".format(
                    n_node_jobs=len(node_jobs),
                    node_id=node_id,
                    work_distribution_file_path=work_distribution_file_path))


def pipeline(args):
    from collections import namedtuple
    from multiprocessing import cpu_count
    from logging import info, warning
    from json import load
    from socket import gethostname

    output_dir_path = args.output_dir_path.resolve()
    work_distribution_file_path = output_dir_path.joinpath(gethostname(
    )).with_suffix('.json')

    try:
        with work_distribution_file_path.open(
                mode='rt') as work_distribution_file:
            work_distribution = load(work_distribution_file)
    except FileNotFoundError:
        warning(
            "Work distribution not found at '{work_distribution_file_path}'. ".format(
                work_distribution_file_path=work_distribution_file_path))
        work_distribution = None  # TODO

    # with TempDir(output_dir_path=output_dir_path, suffix='legal_nlp_pipeline',
    #             directory_permissions=DIRECTORY_PERMISSIONS) as temp_dir:

    extracted_dir_path = output_dir_path.joinpath('1_extracted/')
    tokenized_dir_path = output_dir_path.joinpath('2_tokenized/')
    selected_dir_path = output_dir_path.joinpath('3_selected/')
    parsed_dir_path = output_dir_path.joinpath('4_parsed/')
    trees_dir_path = output_dir_path.joinpath('5_trees/')
    postprocessed_dir_path = output_dir_path.joinpath('6_postprocessed/')
    classf_dir_path = output_dir_path.joinpath('7_simply_classf/')

    SubdirPaths = namedtuple('SubdirPaths', (
        'extracted_dir_path', 'tokenized_dir_path', 'selected_dir_path',
        'parsed_dir_path', 'trees_dir_path', 'postprocessed_dir_path',
        'classf_dir_path'))

    subdir_paths = SubdirPaths(
        extracted_dir_path=extracted_dir_path,
        tokenized_dir_path=tokenized_dir_path,
        selected_dir_path=selected_dir_path,
        parsed_dir_path=parsed_dir_path,
        trees_dir_path=trees_dir_path,
        postprocessed_dir_path=postprocessed_dir_path,
        classf_dir_path=classf_dir_path)

    for subdir_path in subdir_paths:
        if subdir_path.parent == output_dir_path:
            try:
                subdir_path.mkdir(mode=DIRECTORY_PERMISSIONS)
            except FileExistsError:
                warning("Directory '{subdir_path}' already exists. ".format(
                    subdir_path=subdir_path))
                pass
        else:
            info(
                "Skipping '{subdir_path}' as its prefix '{prefix}' is not equal to '{temp_base_dir_path}', "
                "so it is not rooted in the temporary base directory. ".format(
                    subdir_path=subdir_path,
                    prefix=subdir_path.parent,
                    temp_base_dir_path=output_dir_path))

        text_files_suffix = '.txt'
        extract_wraking_texts(
            xml_rulings_dir_path=args.xml_rulings_dir_path,
            work_distribution=work_distribution,
            target_dir_path=subdir_paths.extracted_dir_path,
            out_suffix=text_files_suffix)

        tokenized_files_suffix = text_files_suffix + '.tok'
        alpino_tokenize_text_files(
            extracted_dir_path=subdir_paths.extracted_dir_path,
            target_dir_path=subdir_paths.tokenized_dir_path,
            work_distribution=work_distribution,
            in_suffix=text_files_suffix,
            out_suffix=tokenized_files_suffix)

        # select_tokenized_files(tokenized_dir_path=subdir_paths.tokenized_dir_path,
        #                        target_dir_path=subdir_paths.selected_dir_path,
        #                        work_distribution=work_distribution)

        # selected_tokenized_files = iglob(join(selected_dir_path, '*.sel'))

        n_cores = cpu_count()

        alpino_parse_tokenized_files_directly_multiprocessing(
            tokenized_dir_path=subdir_paths.tokenized_dir_path,
            target_dir_path=subdir_paths.parsed_dir_path,
            n_cores=n_cores,
            work_distribution=work_distribution,
            in_suffix=tokenized_files_suffix)

        # xml_parse_tree_files = iglob(join(parsed_dir_path, '*/*.xml'))
        # render_trees(parsed_dir_path=parsed_dir_path,
        #              target_dir_path=trees_dir_path,
        #              work_distribution=work_distribution)
        # tokenized_files = (join(tokenized_dir_path, ecli, '.xml') for ecli in work_distribution)

        def get_total_work_distribution():
            for json_file_path in output_dir_path.glob('legal*.json'):
                with json_file_path.open(mode='rt') as json_file:
                    a_work_distribution = load(json_file)
                    yield a_work_distribution

        total_work_distribution = \
            chain.from_iterable(a_work_distribution for a_work_distribution in get_total_work_distribution())

        postprocess_parsed_files_multiprocessing(
            parsed_dir_path=subdir_paths.parsed_dir_path,
            target_dir_path=subdir_paths.postprocessed_dir_path,
            work_distribution=total_work_distribution,
            n_cores=n_cores,
            in_suffix='.xml')


if __name__ == '__main__':
    parser = ArgumentParser(
        prog='legal_nlp_pipeline', fromfile_prefix_chars='@')
    parser.add_argument(
        '-v',
        default=INFO,
        type=int,
        help='Verbosity level as integer (the logging module constants). ')
    parser.add_argument('--p', type=Path, help='PID file path. ')
    subparsers = parser.add_subparsers(help='sub-command help')
    parser.set_defaults(func=lambda f: parser.print_help())
    # TODO: make steps of pipeline callable from command line
    fetch_xml_rulings_parser = subparsers.add_parser(
        fetch_and_process_eclis.__name__,
        help='Fetch ECLIS and XML rulings relevant to query. ')
    fetch_xml_rulings_parser.set_defaults(func=fetch_and_process_eclis)
    fetch_xml_rulings_parser.add_argument(
        'xml_rulings_dir_path', type=Path, help='XML rulings directory path. ')
    fetch_xml_rulings_parser.add_argument(
        '--irrelevant_eclis_file_name',
        type=Path,
        default='irrelevant_eclis.pkl',
        help='Irrelevant ECLIs declaration file name. ')
    fetch_xml_rulings_parser.add_argument(
        '--n_max_rulings',
        type=int,
        default=-1,
        help='Maximal number of rulings to fetch by ECLI (-1: all found). ')

    distribute_work_parser = subparsers.add_parser(
        distribute_work.__name__,
        help='Distribute work in terms of ECLIs to be processed in pipeline'
        ' to nodes in cluster. ')
    distribute_work_parser.set_defaults(func=distribute_work)
    distribute_work_parser.add_argument(
        'output_dir_path', type=Path, help='Output directory path. ')
    distribute_work_parser.add_argument(
        'xml_rulings_dir_path', type=Path, help='XML rulings directory path. ')
    distribute_work_parser.add_argument(
        '-cluster_file_name',
        type=str,
        default='cluster.json',
        help='Cluster declaration file path. ')

    pipeline_parser = subparsers.add_parser(
        pipeline.__name__,
        help='Process ECLIs as node in cluster through pipeline according to work '
        'distribution. ')
    pipeline_parser.set_defaults(func=pipeline)
    pipeline_parser.add_argument(
        'output_dir_path', type=Path, help='Output directory path. ')
    pipeline_parser.add_argument(
        'xml_rulings_dir_path', type=Path, help='XML rulings directory path. ')

    args = parser.parse_args()

    if args.p is not None:
        with args.p.open(mode='wt') as pid_file:
            pid = str(getpid())
            pid_file.write(pid)

    basicConfig(
        level=args.v,
        format='%(asctime)s - %(levelname)s - %(message)s')  # TODO: parameterize level

    info('Starting. ')
    try:
        args.func(args)
    except KeyboardInterrupt:
        warning('Interrupted. ')
        raise
    finally:
        info('Exiting. ')
