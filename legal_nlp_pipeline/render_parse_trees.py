from lxml.etree import XPath
from pathlib import Path

# SENTENCE_XPATH = XPath("/alpino_ds/comments[1]/comment[1]")  # TODO: does not work in Alpino server mode??
SENTENCE_XPATH = XPath("/alpino_ds/sentence[1]")  # TODO: does not work in Alpino server mode??
XML_NODES = XPath("/alpino_ds//node[node]/node")


def render_trees(parsed_dir_path: Path, target_dir_path: Path, work_distribution: list):
    from json import dump
    from logging import error, info
    from lxml.etree import parse
    from networkx import DiGraph
    from networkx.readwrite import json_graph
    # from networkx import draw, draw_spring
    from os import mkdir

    for ecli in work_distribution:
        parsed_files_glob = parsed_dir_path.joinpath(ecli).glob('*.xml')

        for parsed_file_path in parsed_files_glob:
            if parsed_file_path.is_file() and parsed_file_path.stat().st_size != 0:
                json_dir_path = target_dir_path.joinpath(ecli)
                if not json_dir_path.is_dir():
                    mkdir(str(json_dir_path))

                json_file_name = parsed_file_path.name + '.json'
                json_file_path = json_dir_path.joinpath(json_file_name)
                # draw_spring(tree)

                if not json_file_path.is_file() or json_file_path.stat().st_size != 0:
                    tree = DiGraph()
                    xml_tree = parse(str(parsed_file_path))
                    sentence = SENTENCE_XPATH(xml_tree)[0].text

                    nodes = []
                    edges = []
                    for xml_node in XML_NODES(xml_tree):
                        lemma = xml_node.get('lemma')
                        pos = xml_node.get('pos')
                        if lemma is None:
                            lemma = '...'
                        node_id = int(xml_node.attrib['id'])
                        node_attributes = {'name': lemma, 'pos': pos}
                        node = (node_id, node_attributes)
                        nodes.append(node)
                        parent_node_id = int(xml_node.getparent().get('id'))
                        edges.append((parent_node_id, node_id))

                    tree.add_nodes_from(nodes)
                    tree.add_edges_from(edges)
                    tree_json = json_graph.tree_data(tree, root=0)

                    wrapper_json = {'origin': parsed_file_path.as_uri(), 'sentence': sentence, 'tree': tree_json}

                    with json_file_path.open(mode='wt') as json_file:
                        dump(wrapper_json, json_file, indent=True)

                    info("Rendered parse tree to '{json_file_path}'. ".format(json_file_path=json_file_path))
            else:
                error("Empty or non-existent XML parse tree file at '{parsed_file_path}'. ".
                      format(parsed_file_path=parsed_file_path))
