from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, DC, DCTERMS, FOAF

FABIO = Namespace('http://purl.org/spar/fabio/')
CITO = Namespace('http://purl.org/spar/cito/')
B4OS = Namespace('http://wallet.blockchain4openscience.com/')
ORE = Namespace('http://www.openarchives.org/ore/terms/')
RMAP = Namespace('http://purl.org/ontology/rmap#')
DOI = Namespace('https://doi.org/')
ORCID = Namespace('https://orcid.org/')
PRISM = Namespace('http://prismstandard.org/namespaces/basic/2.0/')
FRBR = Namespace('http://purl.org/vocab/frbr/core#')


def get_rmap_rdf(author, disco):
    g = Graph()
    n = Namespace("http://wallet.blockchain4openscience.com/")
    disco_node = n[str(disco['_id'])]
    g.add((disco_node, RDF.type, RMAP.DiSCO))
    g.add((disco_node, DC.title, Literal(disco['name'])))
    g.add((disco_node, DCTERMS.description, Literal(disco['description'])))

    id_nodes_map = {}
    author_node = ORCID[author['orcid']]
    g.add((author_node, RDF.type, FOAF.Person))
    g.add((author_node, FOAF.name, Literal(author['name'])))
    research_objects = [node['data'] for node in disco['diagram']['elements']['nodes']]
    for research_object in research_objects:
        if research_object['source'] == 'orcid':
            ro_node = DOI[research_object['id']]
            ro_type = FABIO.JournalArticle
            g.add((ro_node, PRISM.doi, Literal(research_object['id'])))
        elif research_object['source'] == 'figshare':
            ro_node = DOI[research_object['id']]
            ro_type = FABIO.Dataset
        else:
            ro_node = URIRef(research_object['id'])
            ro_type = FABIO.ComputerApplication
        g.add((ro_node, DC.title, Literal(research_object['name'])))
        g.add((ro_node, RDF.type, ro_type))
        g.add((ro_node, DCTERMS.creator, author_node))
        g.add((disco_node, ORE.aggregates, ro_node))
        g.add((ro_node, FRBR.partOf, disco_node))
        id_nodes_map[research_object['id']] = ro_node

    relations = [edge['data'] for edge in disco['diagram']['elements']['edges']]
    for relation in relations:
        g.add((id_nodes_map[relation['source']], CITO.cites, id_nodes_map[relation['target']]))
    return g.serialize(format='turtle')
