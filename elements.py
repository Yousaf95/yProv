from flask import Blueprint, request

from prov.model import ProvDocument
from py2neo.matching import NodeMatcher

from extension import neo4j
from utils import (
    json_to_prov_record,
    prov_element_to_node,
    node_to_prov_element,
    prov_element_to_json,
    set_ns               
)


elements_bp = Blueprint('elements', __name__)

# Create
@elements_bp.route('', methods=['POST'])
def create_element(doc_id):
    try:
        graph = neo4j.get_db(doc_id)
    except:
        return "DB error", 500

    # check if document is in neo4j 
    try:
        assert graph
    except AssertionError:
        return "Document not found", 404

    prov_document = ProvDocument()

    set_ns(graph, prov_document)

    # parsing
    prov_element = json_to_prov_record(request.json, prov_document)
    node = prov_element_to_node(prov_element)

    try:
        graph.create(node)
    except:
        return "DB error", 500

    return "Element created", 201

# Read
@elements_bp.route('/<string:e_id>', methods=['GET'])
def get_element(doc_id, e_id):
    try:
        graph = neo4j.get_db(doc_id)
    except:
        return "DB error", 500

    # check if document is in neo4j 
    try:
        assert graph
    except AssertionError:
        return "Document not found", 404

    # check if element is in document 
    try:
        # match the node
        node_matcher = NodeMatcher(graph)
        node = node_matcher.match('Entity', id=e_id).first() 
        assert(node)
    except AssertionError:
        return "Entity not found", 404
    

    prov_document = ProvDocument()

    set_ns(graph, prov_document)

    prov_element = node_to_prov_element(node, prov_document)

    return prov_element_to_json(prov_element)

# Update
@elements_bp.route('/<string:e_id>', methods=['PUT'])
def replace_element(doc_id, e_id):
    try:
        graph = neo4j.get_db(doc_id)
    except:
        return "DB error", 500

    # check if document is in neo4j 
    try:
        assert graph
    except AssertionError:
        return "Document not found", 404

    # match the node
    node_matcher = NodeMatcher(graph)
    # node = node_matcher.match('Entity', id=e_id).first() 
    node = node_matcher.match(id=e_id).first()


    prov_document = ProvDocument()

    set_ns(graph, prov_document)

    # parsing
    prov_element = json_to_prov_record(request.json, prov_document)
    input_node = prov_element_to_node(prov_element)
    
    # if exist then update else create
    if(node):
        node.clear()
        for key, value in input_node.items():
            node[key]=value

        graph.push(node)

        return "Element updated", 200
    else:
        try:
            graph.create(input_node)
        except:
            return "DB error", 500
        
        return "Element created", 201

# Delete
@elements_bp.route('/<string:e_id>', methods=['DELETE'])
def delete_element(doc_id, e_id):
    try:
        graph = neo4j.get_db(doc_id)
    except:
        return "DB error", 500

    # check if document is in neo4j 
    try:
        assert graph
    except AssertionError:
        return "Document not found", 404

    # check if element is in document 
    try:
        # match the node
        node_matcher = NodeMatcher(graph)
        # node = node_matcher.match('Entity', id=e_id).first() 
        node = node_matcher.match(id=e_id).first()
        assert(node)
    except AssertionError:
        return "Element not found", 404
    
    try:
        graph.delete(node)
    except AssertionError:
        return "DB error", 500

    return "Element deleted", 200