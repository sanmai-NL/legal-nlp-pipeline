from pathlib import Path
from os import getenv

ENCODING = 'utf-8'

# TODO use configuration file
from subprocess import CalledProcessError

ALPINO_HOME = getenv('ALPINO_HOME')
alpino_home_dir_path = Path(ALPINO_HOME)
# ALPINO_EXECUTABLE = 'bin/Alpino'  # relative to ALPINO_HOME
ALPINO_ENV = {'ALPINO_HOME': ALPINO_HOME, 'PATH': getenv('PATH')}
ALPINO_SOCKET_BUFFER_SIZE = 8192  # 4096


def wccount(file_path: Path):
    """
    Count number of lines in a file efficiently.
    """
    from subprocess import Popen, PIPE, STDOUT

    return int(
        Popen(
            ('wc', '-l', str(file_path)), stdout=PIPE,
            stderr=STDOUT).communicate()[0].partition(b' ')[0])


def make_way(path: Path):
    from os import remove
    from shutil import rmtree

    if path.is_dir():
        rmtree(str(path))
    elif path.exists():
        remove(str(path))


def is_ready_to_parse(parsed_sentences_files_dir_path: Path):
    from os import mkdir
    from logging import debug

    lock_file_path = parsed_sentences_files_dir_path.with_suffix('.lock')
    if not parsed_sentences_files_dir_path.exists():  # TODO: is_dire?
        mkdir(str(parsed_sentences_files_dir_path))
        with lock_file_path.open(mode='wb'):
            pass
        return True
    else:
        if lock_file_path.exists():
            debug("Lock in place at {lock_file_path}. ".format(
                lock_file_path=lock_file_path))
        return False


def prepare_parsing(tokenized_file_path: Path, target_dir_path: Path):
    from logging import debug, info, warning

    if tokenized_file_path.is_file() and tokenized_file_path.stat(
    ).st_size != 0:
        ecli = tokenized_file_path.name.split('.')[0]
        parsed_sentences_files_dir_path = target_dir_path.joinpath(ecli)
        # TODO:
        lock_file_path = parsed_sentences_files_dir_path.with_suffix('.lock')

        if is_ready_to_parse(parsed_sentences_files_dir_path):
            debug(
                "Tokenized file at '{tokenized_file_path}' is going to be parsed. ".format(
                    tokenized_file_path=tokenized_file_path))
        else:
            nonzero_parsed_sentence_files = \
                tuple(file_name for file_name in parsed_sentences_files_dir_path.iterdir()
                      if parsed_sentences_files_dir_path.joinpath(file_name).stat().st_size != 0)

            n_nonzero_parsed_sentence_files = len(
                nonzero_parsed_sentence_files)
            tokenized_file_line_count = wccount(tokenized_file_path)
            if n_nonzero_parsed_sentence_files == tokenized_file_line_count:
                info(
                    "Tokenized file at '{tokenized_file_path}' has already been parsed. ".format(
                        tokenized_file_path=tokenized_file_path))
                return None, None
            elif n_nonzero_parsed_sentence_files < tokenized_file_line_count:
                # TODO: make Alpino do partial parses, in case that is helpful.
                if not lock_file_path.exists():
                    warning(
                        "Removing incomplete ({n_nonzero_parsed_sentence_files:d} < {tokenized_file_line_count:d} "
                        "sentences) parsing in '{parsed_sentences_files_dir_path}'. ".format(
                            n_nonzero_parsed_sentence_files=n_nonzero_parsed_sentence_files,
                            tokenized_file_line_count=tokenized_file_line_count,
                            parsed_sentences_files_dir_path=parsed_sentences_files_dir_path))
                    make_way(path=parsed_sentences_files_dir_path)
                    prepare_parsing(
                        tokenized_file_path=tokenized_file_path,
                        target_dir_path=target_dir_path)
                else:
                    return None, None
            elif n_nonzero_parsed_sentence_files > tokenized_file_line_count:
                raise RuntimeError(
                    'More nonzero-size sentences already parsed ({n_nonzero_parsed_sentence_files:d}) '
                    'than were going to be parsed ({tokenized_file_line_count:d}) in '
                    '"{parsed_sentences_files_dir_path}". Is there a mismatch between the previous '
                    'and current contents of "{tokenized_file_path}"? '.format(
                        n_nonzero_parsed_sentence_files=n_nonzero_parsed_sentence_files,
                        tokenized_file_line_count=tokenized_file_line_count,
                        parsed_sentences_files_dir_path=parsed_sentences_files_dir_path,
                        tokenized_file_path=tokenized_file_path))

        parsed_sentence_file_path_prefix = parsed_sentences_files_dir_path.joinpath(
            tokenized_file_path.name)

        return parsed_sentences_files_dir_path, parsed_sentence_file_path_prefix
    else:
        warning(
            "No tokenized file recognized at '{tokenized_file_path}'. ".format(
                tokenized_file_path=tokenized_file_path))


def alpino_parse_tokenized_file_socket(tokenized_file_path: Path,
                                       target_dir_path: Path,
                                       host='127.0.0.1',
                                       base_port_number=42424,
                                       n_instances: int=4):
    """
    Warning: produces corrupt output for half of the sentences.
    """
    from io import BytesIO
    from logging import info
    from random import randrange
    from socket import AF_INET, SOCK_STREAM, socket

    chosen_port = randrange(base_port_number, base_port_number + n_instances)

    parsed_sentences_files_dir_path, parsed_sentence_file_path_prefix = \
        prepare_parsing(tokenized_file_path=tokenized_file_path,
                        target_dir_path=target_dir_path)

    if parsed_sentences_files_dir_path is not None:
        with tokenized_file_path.open(mode='rb') as tokenized_file:
            parsed_sentence_buffer = BytesIO()
            sentence_index = 0

            for sentence in tokenized_file.readlines():
                sentence_index += 1
                with socket(AF_INET, SOCK_STREAM) as alpino_socket:
                    # alpino_socket.settimeout() # TODO: set timeout equal to Alpino timeout
                    alpino_socket.connect_ex((host, chosen_port))
                    alpino_socket.sendall(sentence + b'\n\n')

                    while True:
                        parsed_sentence_xml_chunk = alpino_socket.recv(
                            ALPINO_SOCKET_BUFFER_SIZE)
                        if not parsed_sentence_xml_chunk:
                            alpino_socket.sendall(b'\n\n')
                            break
                        else:
                            parsed_sentence_buffer.write(
                                parsed_sentence_xml_chunk)

                parsed_sentence = parsed_sentence_buffer.getvalue()

                parsed_sentence_buffer.truncate()
                parsed_sentence_buffer.flush()
                parsed_sentence_buffer.seek(0)

                parsed_sentence_file_path = \
                    parsed_sentence_file_path_prefix.with_suffix('.{0:d}.xml'.format(sentence_index))
                with parsed_sentence_file_path.open(
                        mode='wb') as parsed_sentence_file:
                    parsed_sentence_file.write(parsed_sentence)

            info("Parsed tokenized file to '{parsed_sentence_file_path_prefix}'.*.xml . ".format(
                parsed_sentence_file_path_prefix=parsed_sentence_file_path_prefix))

# def alpino_parse_tokenized_files_directly_multithreaded(tokenized_files, target_dir_path: str, n_workers: int=4):
#     """
#     WARNING: Alpino may produce corrupted output if you use this function.
#     """
#     from concurrent.futures import wait, FIRST_EXCEPTION
#     from concurrent.futures.thread import ThreadPoolExecutor
#     from logging import info
#
#     info('Performing parsings (directly, multithreaded) ... ')
#
#     with ThreadPoolExecutor(max_workers=n_workers) as executor:
#         tasks = tuple(executor.submit(postprocess_parsed_file_directly, text_file_path, target_dir_path)  # TODO:
#                       for text_file_path in tokenized_files)
#         done, not_done = wait(tasks, return_when=FIRST_EXCEPTION)
#
#         len_not_done = len(not_done)
#         if len_not_done > 0:
#             raise not_done.pop().exception()
#
#         info('Performed {0:d} parsings, failed to do {1:d}. '.format(len(done), len_not_done))

# def alpino_parse_tokenized_files_socket_multithreaded(tokenized_files_dir_path: Path, target_dir_path: Path,
#                                                       n_instances: int, work_distribution, in_suffix, host='127.0.0.1',
#                                                       base_port_number=42424, ):
#     from concurrent.futures import wait, FIRST_EXCEPTION
#     from concurrent.futures.thread import ThreadPoolExecutor
#     from logging import info
#
#     info('Performing parsings (socket, multithreaded) ... ')
#
#     tokenized_files = (tokenized_files_dir_path.joinpath(ecli).with_suffix(in_suffix) for ecli in work_distribution)
#
#     with ThreadPoolExecutor(max_workers=n_instances) as executor:
#         tasks = tuple(
#             executor.submit(alpino_parse_tokenized_file_socket, tokenized_file_path, target_dir_path)
#             for tokenized_file_path in tokenized_files
#             if tokenized_file_path.is_file() and tokenized_file_path.stat().st_size != 0)  # TODO: error condition
#         done, not_done = wait(tasks, return_when=FIRST_EXCEPTION)
#
#         len_not_done = len(not_done)
#         if len_not_done > 0:
#             raise not_done.pop().exception()
#
#         info('Performed {0:d} parsings, failed to do {1:d}. '.format(len(done), len_not_done))


def alpino_parse_tokenized_files_socket(tokenized_files_dir_path: Path,
                                        target_dir_path: Path,
                                        in_suffix: str,
                                        work_distribution,
                                        n_instances: int,
                                        host='127.0.0.1',
                                        base_port_number=42424):
    from logging import info

    tokenized_files = (
        tokenized_files_dir_path.joinpath(ecli).with_suffix(in_suffix)
        for ecli in work_distribution)

    info('Performing parsings (socket, single-threaded) ... ')
    parsing_count = 0
    for tokenized_file_path in tokenized_files:
        if tokenized_file_path.is_file() and tokenized_file_path.stat(
        ).st_size != 0:
            alpino_parse_tokenized_file_socket(
                tokenized_file_path=tokenized_file_path,
                target_dir_path=target_dir_path)
            parsing_count += 1
        else:
            raise RuntimeError(
                "Tokenized file '{text_file_path}' is not a file or has zero size. ".format(
                    text_file_path=tokenized_file_path))

    info('Performed {0:d} parsings. '.format(parsing_count))


def alpino_parse_tokenized_file_directly(tokenized_file_path: Path,
                                         target_dir_path: Path, cpu_core: str):
    from logging import info, warning, error
    from os import remove
    from subprocess import check_call

    parsed_sentences_files_dir_path, parsed_sentence_file_path_prefix = \
        prepare_parsing(tokenized_file_path=tokenized_file_path,
                        target_dir_path=target_dir_path)
    if parsed_sentences_files_dir_path is not None:
        command = ('taskset', '-a', '-c', cpu_core, 'Alpino', '-veryfast',
                   '-notk', 'assume_input_is_tokenized=on', 'demo=off',
                   'current_ref=1', 'pos_tagger=on', 'user_max=190000',
                   'xml_format_frame=on', 'end_hook=xml', '-flag', 'treebank',
                   str(parsed_sentences_files_dir_path), '-parse')
        with tokenized_file_path.open(mode='rb') as tokenized_file:
            try:
                check_call(
                    command,
                    stdin=tokenized_file,
                    stderr=None,
                    stdout=None,
                    env=ALPINO_ENV,
                    cwd=ALPINO_HOME)  # stdout=DEVNULL
                # TODO: check whether Alpino will overwrite (zero size) parsed sentence files?
            except CalledProcessError:
                error(
                    "Could not parse tokenized file '{tokenized_file_path}'. ".format(
                        tokenized_file_path=tokenized_file_path))
                raise
            else:
                info("Parsed tokenized file to '{parsed_sentence_file_path_prefix}'.*.xml . ".format(
                    parsed_sentence_file_path_prefix=parsed_sentence_file_path_prefix))
            finally:
                # TODO: lock removed at right time?
                lock_file_path = parsed_sentences_files_dir_path.with_suffix(
                    '.lock')
                remove(str(lock_file_path))
    else:
        warning(
            "Skipping tokenized file to be parsed at '{tokenized_file_path}'. ".format(
                tokenized_file_path=tokenized_file_path))


def alpino_parse_tokenized_files_directly_multiprocessing(
        tokenized_dir_path: Path, target_dir_path: Path, n_cores: int,
        in_suffix: str, work_distribution):
    from itertools import cycle
    from logging import info
    from multiprocessing import Pool
    from collections import deque

    cpu_cores = cycle(str(core_index) for core_index in range(0, n_cores))

    info('Performing parsings (directly, multiprocessing) ... ')

    tokenized_files = (tokenized_dir_path.joinpath(ecli).with_suffix(in_suffix)
                       for ecli in work_distribution)

    with Pool(processes=n_cores) as pool:
        futures = deque()

        for tokenized_file_path in tokenized_files:
            if tokenized_file_path.is_file() and tokenized_file_path.stat(
            ).st_size != 0:
                futures.append(
                    pool.apply_async(
                        func=alpino_parse_tokenized_file_directly,
                        args=(tokenized_file_path, target_dir_path, next(
                            cpu_cores))))
            else:
                raise RuntimeError(
                    "Tokenized file at '{tokenized_file_path}' is not a file or has zero size. ".format(
                        tokenized_file_path=tokenized_file_path))

        pool.close()
        for future in futures:
            future.get()

    info("Performed parsings to '{target_dir_path}'. ".format(
        target_dir_path=target_dir_path))
