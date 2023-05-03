from flask import Blueprint, jsonify, request
from prov.model import ProvDocument, ProvElement, ProvRelation
from prov.serializers.provjson import ProvJSONDecoder
from py2neo.data import Subgraph, Node, Relationship
from py2neo import Graph
from prov2neo.encode import encode_graph, encode_value, str_id, node_label, edge_label
from py2neo.cypher import Cursor

from prov.model import ProvDocument, ProvRecord
from prov.graph import INFERRED_ELEMENT_CLASS
from prov.identifier import Namespace

from extension import neo4j
import json
from elements import node_to_json, json_to_node


documents_bp = Blueprint('documents', __name__)

def prov_element_to_node(prov_element):
    # parse attr to props
    props = {}
    for attr in prov_element.attributes:
        props[encode_value(attr[0])] = encode_value(attr[1])
        
    return Node(
        node_label(prov_element),
        id = str_id(prov_element.identifier),
        **props
    )

def prov_relation_to_edge(prov_relation, start_node, end_node):
    # parse attr to props
    props = {}
    for attr in prov_relation.attributes:
        props[encode_value(attr[0])] = encode_value(attr[1])
        
    return Relationship(
        start_node,
        edge_label(prov_relation),
        end_node,
        **props
    )

def prov_to_graph(prov_document):

    s = Subgraph()
    # Returns a new document containing all records having same identifiers unified (including those inside bundles)
    unified = prov_document.unified()
    node_map = dict()

    for element in unified.get_records(ProvElement):
        # union operator: add Node to the Subgraph
        node = prov_element_to_node(element)
        s = s | node
        node_map[element.identifier] = node
    

    for relation in unified.get_records(ProvRelation):
        # taking the first two elements of a relation
        attr_pair_1, attr_pair_2 = relation.formal_attributes[:2]
        # only need the QualifiedName (i.e. the value of the attribute)
        qn1, qn2 = attr_pair_1[1], attr_pair_2[1] # sono gli id degli elementi

        if qn1 and qn2:  # only proceed if both ends of the relation exist
            try:
                if qn1 not in node_map:
                    node_map[qn1] = INFERRED_ELEMENT_CLASS[attr_pair_1[0]](None, qn1)
                if qn2 not in node_map:
                    node_map[qn2] = INFERRED_ELEMENT_CLASS[attr_pair_2[0]](None, qn2)
            except KeyError:
                # Unsupported attribute; cannot infer the type of the element
                continue  # skipping this relation

            start_node = node_map[qn1]
            end_node = node_map[qn2]
            rel = prov_relation_to_edge(relation, start_node, end_node)

            s = s | rel
            
    return s



def parse_node(node):
    x=0


    return x

def graph_to_prov(graph):
    prov_doc = ProvDocument()

    # first add ns
    for el in graph['prefixes']:
        # prov_doc.add_namespace(el['properties'][0])
        continue
    
    for n in graph['nodes']:
        print(node_to_json(n, 'entity'))
        # prov_doc.add_record(ProvRecord(identifier=, attributes=))
    # then add nodes
    # finally add records
    '''
    for n in g.nodes():
        if isinstance(n, ProvRecord):
            prov_doc.add_record(n)
    for _, _, edge_data in g.edges(data=True):
        try:
            relation = edge_data["relation"]
            if isinstance(relation, ProvRecord):
                prov_doc.add_record(relation)
        except KeyError:
            pass
    '''

    return prov_doc



# Get a document
@documents_bp.route('/<string:doc_id>', methods=['GET'])
def get_document(doc_id):

    # get db and check if exists
    graph_db = neo4j.get_db(doc_id)

    try:
        assert graph_db
    except AssertionError:
        # no document
        return "No document", 400
    else:
        # verifica se esiste altra chiamata
        #cursor = graph_db.run('call apoc.export.json.all(null, {stream:true})')

        cursor = graph_db.call.apoc.export.json.all(None, {'stream': 'true'})

        result_str = cursor.evaluate(field='data')
        result_list = result_str.rsplit("\n")

        # useful representation
        graph = {
            'prefixes': [],
            'nodes': [],
            'relationships': []
        }
        for str in result_list:
            obj = json.loads(str)
            if(obj['type']=='node'):
                if('_NsPrefDef' in obj['labels']):
                    # case 1, prefix
                    graph['prefixes'].append(obj)
                else:
                    # case 2, node
                    graph['nodes'].append(obj)
            elif(obj['type']=='relationship'):
                # case 2, node
                graph['relationship'].append(obj)

        # print(graph)

        graph_to_prov(graph)

        return "Here it is your document"

# Get list of documents
@documents_bp.route('', methods=['GET'])
def get_list_documents():
    return neo4j.get_all_dbs()

# Create a document
@documents_bp.route('/<string:doc_id>', methods=['PUT'])
def create_document(doc_id):

    # check if json
    content_type = request.headers.get('Content-Type')
    if (content_type != 'application/json'):
        return 'Content-Type not supported!', 400
    
    graph_db = neo4j.get_db(doc_id)

    try:
        # check if a document with the same id is already in neo4j 
        assert not graph_db

        # get the ProvDocument
        data = request.data
        prov_document = ProvDocument.deserialize(content=data)

        # translate ProvDocument to SubGraph  
        # prov2neo function (works also with bundles)
        # s = encode_graph(prov_document)
        s = prov_to_graph(prov_document)

        # create db and save doc
        graph_db = neo4j.create_db(doc_id)
        graph_db.create(s)

        # add ns
        for ns in prov_document.get_registered_namespaces():
            # print(ns._prefix, ns._uri)
            graph_db.call.n10s.nsprefixes.add(ns._prefix, ns._uri)    # questa procedura fa controllo su prefissi e potrebbe lanciare errori


        return "Document created", 201

    except AssertionError:
        return "Document already exists", 409   
    except:
        return "Document not valid", 400        


# Delete a document
@documents_bp.route('/<string:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    try:
        neo4j.delete_db(doc_id)
    except:
        return "Document doesnt exist", 404
    else:
        return "Document deleted", 201