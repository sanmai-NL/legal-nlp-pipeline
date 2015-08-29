from pathlib import Path

def elephant_tokenize_text_files_directly(labeled, out, iob=False):
    if iob:
        for ch, label in labeled:
            out.write(u'{0}\t{1}\n'.format(int(ch), label))
    else:
        first = True
        token_count = 0
        for ch, label in labeled:
            if label == 'S':
                if not first:
                    out.write(u'\n\n')
                    token_count = 1
                first = False
                out.write(u'\n0 ')
            if label == 'T':
                out.write(u'\n{0} '.format(token_count))
                token_count += 1
            if label in 'STI':
                out.write(chr(int(ch)))


def elephant_tokenize_text_file_directly(elephant_dir_path: Path):
    raise NotImplementedError()
    from elephant import check_model_type, label, output_labels_as_string
    from logging import info, debug

    info("Elephant directory path '{elephant_dir_path}'. ".format(elephant_dir_path=elephant_dir_path))

    model_dir_path = str(elephant_dir_path.joinpath('models', 'dutch').resolve())
    info('Elephant models directory path = "{model_dir_path}". '.format(model_dir_path=model_dir_path))

    wapiti_model, elman_model, vocab_model = check_model_type(model_dir_path)

    text = 'Dit is een tekst. En dit ook. '
    info('Ready')
    labeled = label(text, wapiti_model, elman_model, vocab_model)
    # elephant.output_labels(labeled, iob=iob)

    val = output_labels_as_string(labeled, iob=False)
    info(val)

    text = 'Nog een tekst. '
    labeled = label(text, wapiti_model, elman_model, vocab_model)

    val = output_labels_as_string(labeled, iob=False)
    info(val)
    assert False
