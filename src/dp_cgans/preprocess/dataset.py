import pickle
import random

import numpy as np
import pandas as pd
import rdflib
from rdflib import Namespace, URIRef
from rdflib.query import Result

from dp_cgans.embeddings import log
from dp_cgans.preprocess import HPOHeaders
from dp_cgans.preprocess.utils import get_orpha_iri


def generate_synthetic_data(file, seen_rd_file, unseen_rd_file, patients_per_rd=10, use_ontology_rds=True, gen_small_file=False, print_every=0, del_col_th=0, sort=True, verbose = True):
    frequency_dict = {  # frequency ids + associated probability
        28405: 1,  # Obligate (100%)
        28412: 0.895,  # Very frequent (99-80%)
        28419: 0.545,  # Frequent (79-30%)
        28426: 0.17,  # Occasional (29-5%)
        28433: 0.025,  # Very rare (<4-1%)
        28440: 0  # Excluded (0%)
    }

    log(f"📖 Progress: Reading HPO Products Dataset (csv)...", verbose)
    df = pd.read_csv(file)

    log(f"📖 Progress: Create Orpha URI from OrphaCode...", verbose)
    df['Orpha_URI'] = get_orpha_iri(df[HPOHeaders.ORPHA_CODE.value].astype(str))

    log(f"📖 Progress: Reading Seen Rare Disease Pickle File (pkl)...", verbose)
    with open(seen_rd_file, 'rb') as f:
        seen_rds_set = pickle.load(f)

    log(f"📖 Progress: Reading Unseen Rare Disease Pickle File (pkl)...", verbose)
    with open(unseen_rd_file, 'rb') as f:
        unseen_rds_set = pickle.load(f)

    log(f"📖 Progress: Combine both sets together...", verbose)
    df = df.loc[df['Orpha_URI'].isin(seen_rds_set.union(unseen_rds_set))]

    if gen_small_file:
        log(f"📖 Progress: Minify Data to ensure smaller file sizes...", verbose)
        grouped = df.groupby(HPOHeaders.NAME.value, sort=False)
        df = pd.concat([group for name, group in grouped][:10])

    log(f"📖 Progress: Group Rare Diseases with same names...", verbose)
    grouped = df.groupby(HPOHeaders.NAME.value, sort=False)

    rd_count = grouped.ngroups
    unique_hps = df[HPOHeaders.HPO_TERM.value].unique()
    total_hp_count = len(unique_hps)

    log(f"📖 Info: There are {rd_count} unique Rare Diseases.", verbose)
    log(f"📖 Info: There are {total_hp_count} unique Phenotypes.", verbose)

    phenotypes = unique_hps.tolist()
    phenotypes_dict = {
        hp: i for i, hp in enumerate(phenotypes)
    }

    header = [['rare_disease'] + phenotypes]
    seen_patients_data = []
    unseen_patients_data = []

    distribution_check = {  # value: count of patients with hp + maximum count of patients that could've had the hp
        28405: [0, 0],  # Obligate (100%)
        28412: [0, 0],  # Very frequent (99-80%)
        28419: [0, 0],  # Frequent (79-30%)
        28426: [0, 0],  # Occasional (29-5%)
        28433: [0, 0],  # Very rare (<4-1%)
        28440: [0, 0]  # Excluded (0%)
    }

    patients_count = 0

    if not use_ontology_rds:
        vectorize = np.vectorize(get_orpha_iri)
        seen_rds = vectorize(df[HPOHeaders.ORPHA_CODE.value].unique())
        unseen_rds = []





def create_training_and_test_dataset(sparql_url: str, directory: str, verbose: bool = True):
    graph = rdflib.Graph(store="SPARQLStore")
    graph.open(sparql_url)
    graph.bind("HOOM", Namespace("http://www.semanticweb.org/ontology/HOOM"))
    graph.bind("rdf", Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
    graph.bind("owl", Namespace("ttp://www.w3.org/2002/07/owl#"))

    rd_group_dictionary, rd_set, rd_list = build_dictionary(graph)

    seen = [
        "http://www.orpha.net/ORDO/Orphanet_231401",  # Alpha-thalassemia-myelodysplastic syndrome
        "http://www.orpha.net/ORDO/Orphanet_29073",  # Multiple myeloma
        "http://www.orpha.net/ORDO/Orphanet_729",  # Polycythemia vera
        "http://www.orpha.net/ORDO/Orphanet_3226",  # Deafness-lymphedema-leukemia syndrome
        "http://www.orpha.net/ORDO/Orphanet_86843",  # Acute panmyelosis with myelofibrosis
        "http://www.orpha.net/ORDO/Orphanet_98827",  # Unclassified myelodysplastic syndrome
        "http://www.orpha.net/ORDO/Orphanet_514",  # Acute monoblastic/monocytic leukemia
        "http://www.orpha.net/ORDO/Orphanet_517",  # Acute myelomonocytic leukemia
        "http://www.orpha.net/ORDO/Orphanet_318",  # Acute erythroid leukemia
        "http://www.orpha.net/ORDO/Orphanet_824",  # Primary myelofibrosis
        "http://www.orpha.net/ORDO/Orphanet_520",  # Acute promyelocytic leukemia
        "http://www.orpha.net/ORDO/Orphanet_139399"  # Adrenomyeloneuropathy
    ]
    unseen = [
        "http://www.orpha.net/ORDO/Orphanet_3318",  # Essential thrombocythemia
        "http://www.orpha.net/ORDO/Orphanet_521",  # Chronic myeloid leukemia
        "http://www.orpha.net/ORDO/Orphanet_512"  # Metachromatic leukodystrophy
    ]

    seen_rds, unseen_rds = populate_rd_sets(rd_set=rd_set, rd_list=rd_list, rd_groups_dict=rd_group_dictionary, method='selected_rds', selected_seen_rds=seen, selected_unseen_rds=unseen)

    log(f"📖 Saving: Storing Seen Rare Disease Dataset to pickle file...", verbose)
    with open(f'{directory}/seen.pkl', 'wb') as f:
        pickle.dump(seen_rds, f)

    log(f"📖 Saving: Storing Unseen Rare Disease Dataset to pickle file...", verbose)
    with open(f'{directory}/unseen.pkl', 'wb') as f:
        pickle.dump(unseen_rds, f)

    log(f"✅ Success! The seen and unseen Rare Disease Sets have been created and stored in pickle files.",
        verbose)


def populate_rd_sets(rd_set: set, rd_list: list, rd_groups_dict: dict, method: str = "no_groups", shuffle: bool = False, unseen_percentage: float = 0.2, selected_seen_rds: list = [], selected_unseen_rds: list = [], verbose: bool = True):
    log(f"📖 Progress: Initializing Populating Rare Disease Sets...", verbose)

    seen_rds_set = set()
    unseen_rds_set = set()

    log(f"📖 Progress: Establishing selected method", verbose)
    methods = {
        "no_groups",
        "parts_groups",
        "whole_groups",
        "selected_rds"
    }

    if method not in methods:
        raise Exception(f"Method {method} is not an option from {methods}")

    log(f"📖 Progress: The following method will be performed: {method}", verbose)
    total_rds = len(rd_set)

    if method == "no_groups":
        indexes = [i for i in range(len(rd_list))]

        if shuffle:
            log(f"📖 Progress: Shuffling...", verbose)
            random.shuffle(indexes)

        log(f"📖 Progress: Creating seen and unseen Rare Disease Sets...", verbose)
        for ind in indexes:
            rd = rd_list[ind]

            if (rd not in seen_rds_set) and (rd not in unseen_rds_set):
                if len(unseen_rds_set) > total_rds * unseen_percentage:
                    seen_rds_set.add(rd)
                else:
                    unseen_rds_set.add(rd)

    elif method == "parts_groups":
        keys = list(rd_groups_dict.keys())

        if shuffle:
            log(f"📖 Progress: Shuffling...", verbose)
            random.shuffle(keys)

        log(f"📖 Progress: Creating seen and unseen Rare Disease Sets...", verbose)
        for group in keys:
            rds = rd_groups_dict[group]

            unseen_count = 0

            if len(unseen_rds_set) > total_rds * unseen_percentage:
                unseen_count = len(unseen_rds_set)

            for rd in rds:
                if rd in unseen_rds_set:
                    unseen_count += 1
                else:
                    unseen_rds_set.add(rd)
                    unseen_count += 1

    elif method == "whole_groups":
        keys = list(rd_groups_dict.keys())

        if shuffle:
            log(f"📖 Progress: Shuffling...", verbose)
            random.shuffle(keys)

        log(f"📖 Progress: Creating seen and unseen Rare Disease Sets...", verbose)
        for group in keys:
            rds = rd_groups_dict[group]

            if len(unseen_rds_set) > total_rds * unseen_percentage:
                for rd in rds:
                    if (rd not in seen_rds_set) and (rd not in unseen_rds_set):
                        seen_rds_set.add(rd)

    elif method == "selected_rds":
        log(f"📖 Progress: Creating unseen Rare Disease Sets...", verbose)
        for rd in selected_unseen_rds:
            if rd in rd_set:
                if rd not in unseen_rds_set:
                    unseen_rds_set.add(rd)
            else:
                raise Exception(f"The Rare Disease {rd} is unknown")

        log(f"📖 Progress: Creating seen Rare Disease Sets...", verbose)
        if len(selected_seen_rds):
            for rd in selected_seen_rds:
                if rd in rd_set:
                    if (rd not in seen_rds_set) and (rd not in unseen_rds_set):
                        seen_rds_set.add(rd)
                else:
                    raise Exception(f"The Rare Disease {rd} is unknown")
        else:
            for rds in rd_groups_dict.values():
                for rd in rds:
                    if (rd not in seen_rds_set) and (rd not in unseen_rds_set):
                        seen_rds_set.add(rd)

    if method not in ["no_groups", "selected_rds"]:
        log(f"📖 Progress: method indicated grouping of diseases it taking place. Therefore, an additional step is performed to add them to the seen Rare Disease Sets...", verbose)
        # TODO: allow some of these to be added to unseen_rds_set?
        # adding the RDs that aren't part of a RD group, in the seen set
        for rd in rd_list:
            if (rd not in seen_rds_set) and (rd not in unseen_rds_set):
                seen_rds_set.add(rd)

    log(f"📖 Info: The number of seen Rare Diseases is {len(seen_rds_set)} ({(len(seen_rds_set) / len(rd_set) * 100):.2f}%)", verbose)
    log(f"📖 Info: The number of unseen Rare Diseases is {len(unseen_rds_set)} ({(len(unseen_rds_set) / len(rd_set) * 100):.2f}%)", verbose)

    log(f"✅ Success! The seen and unseen Rare Disease Sets have been created.",
        verbose)

    return seen_rds_set, unseen_rds_set


def build_dictionary(graph: rdflib.Graph, verbose: bool = True):
    rd_list = []
    rd_groups_dict = {}

    log("📖 Querying: Retrieving Rare Disease Association Classes", verbose)
    rds_associated_classes_query = query_get_rare_diseases_association_classes(graph)

    log("📖 Processing: Assigning Association Classes to list of rare diseases", verbose)
    for row in rds_associated_classes_query:
        rd_list.append(str(row.rd))

    rd_set = set(rd_list)

    log("📖 Querying: Retrieving Rare Disease including their group", verbose)
    rds_corresponding_groups_query = query_get_rare_diseases_with_group(graph)

    log("📖 Processing: building Dictionary of Groups and their Association Rare Diseases", verbose)
    for row in rds_corresponding_groups_query:
        rd = str(row.rd)
        group = str(row.group)

        if rd in rd_set:
            if group not in rd_groups_dict:
                rd_groups_dict[group] = []

            if rd not in rd_groups_dict[group]:
                rd_groups_dict[group].append(rd)

    log(f"📖 Info: The number of unique, seen in Associated class Rare Diseases are {len(rd_list)}, {len(rd_set)}", verbose)
    log(f"📖 Info: The number of Rare Disease Groups is {len(rd_groups_dict)}", verbose)
    len_sum = sum(len(dct) for dct in rd_groups_dict.values())

    log(f"📖 Info: The total number of rare diseases in the groups are {len_sum}",
        verbose)
    log(f"📖 Info: The Average amount of Rare Diseases per group is {len_sum / len(rd_groups_dict)}",
        verbose)

    log(f"✅ Success! The dictionary has been successfully build",
        verbose)
    return rd_groups_dict, rd_set, rd_list

def query_get_rare_diseases_with_group(graph: rdflib.Graph) -> Result:
    query = """
    SELECT ?rd ?group
    WHERE {
      ?rd a owl:Class .
      ?group a owl:Class .
      ?rd rdfs:subClassOf [ 
        a owl:Restriction ;
        owl:onProperty <http://purl.obolibrary.org/obo/BFO_0000050> ;
        owl:someValuesFrom ?group
      ] .
    }
    """

    return graph.query(query)


def query_get_rare_diseases_association_classes(graph: rdflib.Graph) -> Result:
    query = """
    SELECT DISTINCT ?rd
    {
        ?subject rdfs:subClassOf HOOM:Association .
        BIND(REPLACE(STR(?subject), ".*Orpha:([0-9]+).*", "$1") AS ?sub) .
        BIND(CONCAT("http://www.orpha.net/ORDO/Orphanet_", ?sub) AS ?rd) .
    }
    """

    return graph.query(query)


def query_get_rare_diseases_by_subgroup(graph: rdflib.Graph, uri: str) -> Result:
    query = """
    SELECT DISTINCT ?rd ?label
    {
        ?subject rdfs:subClassOf HOOM:Association .
        BIND(REPLACE(STR(?subject), ".*Orpha:([0-9]+).*", "$1") AS ?sub) .
        BIND(CONCAT("http://www.orpha.net/ORDO/Orphanet_", ?sub) AS ?rd_1) .
  		BIND (URI(?rd_1) AS ?rd_uri) .
  
        ?rd_uri rdfs:subClassOf [ 
          a owl:Restriction ;
          owl:onProperty <http://purl.obolibrary.org/obo/BFO_0000050> ;
          owl:someValuesFrom ?given_uri
        ] .
  		OPTIONAL { ?rd_uri rdfs:label ?label}
  		BIND (STR(?rd_uri) AS ?rd) .
  		FILTER REGEX(?label, "[^ORPHA:0-9]") .
    }
    """

    return graph.query(query, initBindings={ 'given_uri': URIRef(uri)})


def query_get_rare_diseases_by_word(graph: rdflib.Graph, word: str) -> Result:
    """
    Retrieves the Association classes that contain a specific given word.

    TODO: use `initBindings` instead of a potentially `unsafe` escape. \
        The issue with this is that `Literal(word)` would give an empty result, \
        and none of the other aspects seem to work either.

    Args:
        graph: the Graph to read from
        word: the word to filter by

    Returns: the results of the query

    """

    query = """
    SELECT DISTINCT ?rd ?label
    {
        ?subject rdfs:subClassOf HOOM:Association .
        BIND(REPLACE(STR(?subject), ".*Orpha:([0-9]+).*", "$1") AS ?sub) .
        BIND(CONCAT("http://www.orpha.net/ORDO/Orphanet_", ?sub) AS ?rd_1) .
  		BIND (URI(?rd_1) AS ?rd_uri) .

  		OPTIONAL { ?rd_uri rdfs:label ?label}
  		BIND (STR(?rd_uri) AS ?rd) .
  		FILTER REGEX(?label, "[^ORPHA:0-9]") .
  		FILTER CONTAINS(?label, \"""" + word + """\") .
    }
    """

    return graph.query(query)