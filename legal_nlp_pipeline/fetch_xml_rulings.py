from collections.abc import Iterable
# from multiprocessing import Queue
from pathlib import Path

NAMESPACE_PREFIX_MAP = {'atom': 'http://www.w3.org/2005/Atom',
                        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                        'ecli': 'https://e-justice.europa.eu/ecli',
                        'tr': 'http://tuchtrecht.overheid.nl/',
                        'eu': 'http://publications.europa.eu/celex/',
                        'dcterms': 'http://purl.org/dc/terms/',
                        'bwb': 'bwb-dl',
                        'cvdr': 'http://decentrale.regelgeving.overheid.nl/cvdr/',
                        'psi': 'http://psi.rechtspraak.nl/',
                        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                        'rvr': 'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}

ECLI_XPATH_SPEC = '/atom:feed/atom:entry/atom:id[1]/text()'
EXPECTED_CONTENT_TYPE_ATOM = 'application/atom+xml'
EXPECTED_CONTENT_TYPE_XML = 'application/xml'
NUMBER_OF_ECLIS_XPATH_SPEC = '/atom:feed/atom:subtitle[1]/text()'
PROCEDURE_WRAKING = 'http://psi.rechtspraak.nl/procedure#wraking'
RULING_DATA_URL_PREFIX = 'http://data.rechtspraak.nl/uitspraken/content?id='
RULING_FILTER_XPATH_SPEC = '/open-rechtspraak/rdf:RDF[1]/rdf:Description[1]/psi:procedure[1]/@resourceIdentifier[1]'
ZOEKEN_URL_PREFIX = 'http://data.rechtspraak.nl/uitspraken/zoeken?'


def fetch(url: str, expected_content_type: str):
    from contextlib import closing
    from http.client import OK
    from logging import exception, warning
    from lxml.etree import XML, XMLSyntaxError
    from socket import timeout
    from urllib.request import urlopen

    warning_message = ''
    try:
        try:
            with closing(urlopen(url, timeout=60)) as response:  # TODO: parameterize
                content_type = response.info().get_content_type()
                http_response_code = response.getcode()
                if http_response_code == OK and content_type == expected_content_type:
                    data = response.read()
                    if content_type == EXPECTED_CONTENT_TYPE_ATOM or EXPECTED_CONTENT_TYPE_XML:
                        try:
                            tree = XML(data)
                        except XMLSyntaxError:
                            exception("Data from '{url:s}' is ill-formed XML. Data:\n{data:s}".
                                      format(url=url, data=data.decode()))
                            raise
                        else:
                            return tree
                    else:
                        return data
                else:
                    warning_message = "Unexpected HTTP status code and/or content type of response. The HTTP "
                    "response code is {http_response_code:d}. Response content is of type "
                    "'{content_type:s}', expected '{expected_content_type:s}'". \
                        format(http_response_code=http_response_code,
                               expected_content_type=expected_content_type,
                               content_type=content_type)
                    raise ValueError(warning_message)
        except timeout:
            warning_message = "Fetching URL '{url:s}' did not complete within 60 seconds. ".format(url=url)
            raise
    except (timeout, ValueError) as e:
        final_warning_message = "Fetching URL '{url:s}' failed. ".format(url=url)
        warning(final_warning_message + warning_message)
        raise ResourceWarning(warning_message) from e


def distribute_remainder_over_range_indices(start, stop, step, remainder):
    indices = []
    while stop - start > 0:
        indices.append(start)
        if remainder > 0:
            start = start + step + 1
            remainder -= 1
        else:
            start = start + step
    indices.append(stop)
    return indices


# def sanitize_xml_bytes(xml: bytes):
#     return xml.replace(b'&euml;', b'&#235;')

def process_eclis(relevant_eclis: Iterable, ruling_filter_xpath_spec: str, data_dir_path: Path, logger):
    """
    :param relevant_eclis:
    :param ruling_filter_xpath_spec:
    :param data_dir_path:
    :param logger:
    :yield: any irrelevant ECLI as string or None
    """
    from lxml.etree import XPath, tostring
    from time import sleep

    ruling_filter_xpath = XPath(ruling_filter_xpath_spec, namespaces=NAMESPACE_PREFIX_MAP)
    backoff_time = 10

    for ecli in relevant_eclis:
        try:
            ecli_file_path = data_dir_path.joinpath(ecli).with_suffix('.xml')
            if not ecli_file_path.is_file() or ecli_file_path.stat().st_size == 0:  # TODO: seems not to work??
                url = RULING_DATA_URL_PREFIX + ecli

                try:
                    ruling_tree = fetch(url=url, expected_content_type=EXPECTED_CONTENT_TYPE_XML)
                except ResourceWarning:
                    logger.error(
                        'Will back off {backoff_time:s} s now and continue. '.format(backoff_time=backoff_time))
                    sleep(backoff_time)  # TODO make backoff_time delay configurable
                    continue
                else:
                    procedure = ruling_filter_xpath(ruling_tree)[0]

                    if procedure == PROCEDURE_WRAKING:  # TODO: Make configurable
                        logger.info("Including ruling '{ecli:s}'. ".format(ecli=ecli))
                        with ecli_file_path.open(mode='wb') as ecli_file:
                            ecli_file.write(tostring(ruling_tree, encoding='utf-8', pretty_print=True))
                    else:
                        logger.info("Excluding ruling '{ecli:s}'. ".format(ecli=ecli))
                        logger.debug("Ruling '{ecli:s}' is of procedure type '{procedure:s}'. ".
                                     format(ecli=ecli, procedure=procedure))

                        yield ecli
            else:
                logger.info("Data for ruling ruling '{ecli:s}' has already been fetched. "
                            "Skipped fetching data ... ".format(ecli=ecli))
        except (RuntimeError, ResourceWarning) as e:  # TODO: narrow down
            logger.error(str(e))
            yield
            continue


def process_ecli_batch(xml_rulings_dir_path: Path, data_dir_path: Path, complete_query: str,
                       previous_irrelevant_eclis: frozenset, log_level: int):
    from logging import basicConfig, getLogger, getLevelName
    from lxml.etree import parse, XPath, tostring
    # from multiprocessing import get_logger

    basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')  # TODO: parameterize level
    logger = getLogger(process_ecli_batch.__name__)
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)  # TODO: Why oh why is this needed??
    logger.warning("Log level = {0}.".format(getLevelName(getLogger().getEffectiveLevel())))

    ecli_batch_file_path = xml_rulings_dir_path.joinpath(complete_query + '.xml')
    if not ecli_batch_file_path.is_file() or ecli_batch_file_path.stat().st_size == 0:
        url = ZOEKEN_URL_PREFIX + complete_query

        try:
            ecli_batch_tree = fetch(url=url, expected_content_type=EXPECTED_CONTENT_TYPE_ATOM)
        except ResourceWarning:
            raise RuntimeError('Cannot work without ECLIs batch data. ')
        else:
            logger.info("Fetched batch of ECLIs from URL '{url:s}' to '{ecli_batch_file_path}'. ".
                        format(url=url, ecli_batch_file_path=ecli_batch_file_path))
    else:
        ecli_batch_tree = parse(str(ecli_batch_file_path))

    # Cannot be global due to multiprocessing:
    ecli_xpath = XPath(ECLI_XPATH_SPEC, namespaces=NAMESPACE_PREFIX_MAP)
    relevant_eclis = (ecli for ecli in ecli_xpath(ecli_batch_tree) if
                      ecli not in previous_irrelevant_eclis)
    del ecli_xpath
    with ecli_batch_file_path.open(mode='wb') as ecli_batch_file:
        ecli_batch_file.write(tostring(ecli_batch_tree))

    return frozenset(ecli for ecli in process_eclis(relevant_eclis=relevant_eclis,
                                                    ruling_filter_xpath_spec=RULING_FILTER_XPATH_SPEC,
                                                    data_dir_path=data_dir_path,
                                                    logger=logger) if ecli is not None)


def fetch_and_process_eclis(args):
    from collections import deque
    from contextlib import closing
    from logging import getLogger, warning, info
    from lxml.etree import XPath
    from multiprocessing import cpu_count, Pool
    from pickle import dump, load, HIGHEST_PROTOCOL
    from re import compile

    # TODO: why use query_size?
    # query_size = 1000
    # query1 = 'date=2012-01-01&date=2015-08-01T00:00:00&return=DOC&max=1000&type=Uitspraak&' \
    #          'subject=http%3A%2F%2Fpsi.rechtspraak.nl%2Frechtsgebied%23strafrecht'
    query = 'date=2010-01-01&date=2015-08-01T00:00:00&return=DOC&type=Uitspraak'
    # TODO: factor out query templates, make configurable
    polling_query = 'max=0&{query:s}'.format(query=query)  # TODO: performance
    url = ZOEKEN_URL_PREFIX + polling_query

    try:
        n_eclis_tree = fetch(url=url, expected_content_type=EXPECTED_CONTENT_TYPE_ATOM)
    except ResourceWarning:
        if args.n_max_rulings == -1:
            raise RuntimeError("Cannot work without n_max_rulings: both unspecified and undetermined from '{url}'. "
                               .format(url=url))
    number_of_eclis_xpath = XPath(NUMBER_OF_ECLIS_XPATH_SPEC, namespaces=NAMESPACE_PREFIX_MAP)
    number_of_eclis_xpath_regex = compile(r"Aantal gevonden ECLI's: (\d+)")
    n_eclis_determined = int(number_of_eclis_xpath_regex.match(number_of_eclis_xpath(n_eclis_tree)[0]).groups(0)[0])
    del number_of_eclis_xpath, number_of_eclis_xpath_regex
    if args.n_max_rulings != -1:
        n_eclis = min(n_eclis_determined, args.n_max_rulings)
    else:
        n_eclis = n_eclis_determined

    n_workers = cpu_count()  # TODO: normalize
    n_requests_per_worker, remainder = divmod(n_eclis, n_workers)
    rulings_ranges_indices = distribute_remainder_over_range_indices(0, n_eclis, n_requests_per_worker,
                                                                     remainder)

    xml_rulings_dir_path = args.xml_rulings_dir_path
    data_dir_path = xml_rulings_dir_path.joinpath('data')
    irrelevant_eclis_file_path = xml_rulings_dir_path.joinpath(args.irrelevant_eclis_file_name)

    previous_irrelevant_eclis = frozenset()
    if not xml_rulings_dir_path.is_dir():  # TODO: exists?
        xml_rulings_dir_path.mkdir()
        data_dir_path.mkdir()  # TODO: set mode
    else:
        if irrelevant_eclis_file_path.is_file() and irrelevant_eclis_file_path.stat().st_size != 0:
            with irrelevant_eclis_file_path.open(mode='rb') as previous_irrelevant_eclis_file:
                previous_irrelevant_eclis = \
                    frozenset(load(file=previous_irrelevant_eclis_file))
                # TODO: security
        else:
            warning("Previous irrelevant rulings file at '{irrelevant_eclis_file_path}' does not exist or has "
                    "zero size.".format(irrelevant_eclis_file_path=irrelevant_eclis_file_path))

        if not data_dir_path.is_dir():  # TODO: exists?
            data_dir_path.mkdir()

    log_level = getLogger().getEffectiveLevel()
    # info('Log level = {0:d}'.format(log_level))
    # from sys import exit
    # exit(0)
    # logger = getLogger(
    # get_logger()  # TODO:
    # logger.setLevel(log_level)

    with Pool(processes=n_workers) as pool:
        futures = deque()
        min_index = 0
        with closing(pool):
            for max_index in rulings_ranges_indices:
                if max_index > 0:
                    complete_query = 'from={min_index:d}&max={max_index:d}&{query:s}'. \
                        format(min_index=min_index, max_index=max_index, query=query)

                    futures.append(pool.apply_async(
                        func=process_ecli_batch,
                        args=(xml_rulings_dir_path, data_dir_path, complete_query, previous_irrelevant_eclis,
                              log_level)))

                    min_index = max_index
        try:
            irrelevant_eclis_tuple = tuple(frozenset(future.get()) for future in futures)
        except TypeError as e:
            raise RuntimeError('The futures to irrelevant ECLIs did not result in actual values for at least one '
                               'worker. Something went wrong with the multiprocessing pool in ' +
                               fetch_and_process_eclis.__name__) from e  # TODO: reword
        else:
            irrelevant_eclis = frozenset.union(previous_irrelevant_eclis, *irrelevant_eclis_tuple)

            info('Dumping irrelevant ECLIs to {irrelevant_eclis_file_path}'.format(
                irrelevant_eclis_file_path=irrelevant_eclis_file_path))
            with irrelevant_eclis_file_path.open(mode='wb') as irrelevant_eclis_file:
                dump(irrelevant_eclis, irrelevant_eclis_file, HIGHEST_PROTOCOL)
