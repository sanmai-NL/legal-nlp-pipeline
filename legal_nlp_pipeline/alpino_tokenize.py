from pathlib import Path

from legal_nlp_pipeline.parse_rulings_texts import ALPINO_ENV, alpino_home_dir_path, ALPINO_HOME

ALPINO_TOKENIZE_EXECUTABLE = str(alpino_home_dir_path.joinpath('Tokenization', 'tokenize.sh'))


def alpino_tokenize_text_file(text_file_path: Path, target_dir_path: Path, out_suffix: str):
    from logging import debug, info, warning
    from subprocess import check_call, DEVNULL

    if text_file_path.is_file() and text_file_path.stat().st_size != 0:
        tokenized_file_path = target_dir_path.joinpath(text_file_path.name).with_suffix(out_suffix)
        if not tokenized_file_path.is_file() or tokenized_file_path.stat().st_size == 0:
            command = (ALPINO_TOKENIZE_EXECUTABLE,)
            with text_file_path.open(mode='rb') as text_file:
                with tokenized_file_path.open(mode='wb') as tokenized_text_file:
                    check_call(command, stdin=text_file, stdout=tokenized_text_file, env=ALPINO_ENV,
                               cwd=ALPINO_HOME)  # stderr=DEVNULL
                    info("Tokenized to '{tokenized_file_path}'. ".format(tokenized_file_path=tokenized_file_path))
        else:
            debug("Tokenized file at '{tokenized_file_path}' already exists and has nonzero size. Skipping. ".
                  format(tokenized_file_path=tokenized_file_path))
    else:
        warning("Text file at '{text_file_path}' does not exist or is empty. Skipping. ".
                format(text_file_path=text_file_path))


def alpino_tokenize_text_files(extracted_dir_path: Path, target_dir_path: Path, in_suffix: str, out_suffix: str,
                               work_distribution):
    from logging import info

    info('Tokenizing texts ...')

    text_files_paths = (extracted_dir_path.joinpath(ecli).with_suffix(in_suffix) for ecli in work_distribution)
    for text_file_path in text_files_paths:
        if text_file_path.is_file() or text_file_path.stat().st_size == 0:
            alpino_tokenize_text_file(text_file_path=text_file_path, target_dir_path=target_dir_path,
                                      out_suffix=out_suffix)
        else:
            raise RuntimeError("Extracted text file '{text_file_path}' is not a file or has zero size. ".
                               format(text_file_path=text_file_path))

    info("Tokenized texts to '{target_dir_path}'.".format(target_dir_path=target_dir_path))
