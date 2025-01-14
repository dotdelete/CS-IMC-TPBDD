import os

import dotenv
import pyodbc
from py2neo import Graph
from py2neo.bulk import create_nodes, create_relationships
from py2neo.data import Node

dotenv.load_dotenv(override=True)

server = os.environ["TPBDD_SERVER"]
database = os.environ["TPBDD_DB"]
username = os.environ["TPBDD_USERNAME"]
password = os.environ["TPBDD_PASSWORD"]
driver= os.environ["ODBC_DRIVER"]

neo4j_server = os.environ["TPBDD_NEO4J_SERVER"]
neo4j_user = os.environ["TPBDD_NEO4J_USER"]
neo4j_password = os.environ["TPBDD_NEO4J_PASSWORD"]

graph = Graph(neo4j_server, auth=(neo4j_user, neo4j_password))

BATCH_SIZE = 10000

print("Deleting existing nodes and relationships...")
graph.run("MATCH ()-[r]->() DELETE r")
graph.run("MATCH (n:Artist) DETACH DELETE n")
graph.run("MATCH (n:Film) DETACH DELETE n")

with pyodbc.connect('DRIVER='+driver+';SERVER=tcp:'+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password) as conn:
    cursor = conn.cursor()

    # Films
    exportedCount = 0
    cursor.execute("SELECT COUNT(1) FROM TFilm")
    totalCount = cursor.fetchval()
    cursor.execute("SELECT idFilm, primaryTitle, startYear FROM TFilm")
    while True:
        importData = []
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break

        i = 0
        for row in rows:
            # Créer un objet Node avec comme label Film et les propriétés adéquates
            # A COMPLETER
            n = Node("Film", idFilm=row[0], primaryTitle=row[1], startYear=row[2])
            importData.append(n)
            i += 1

        try:
            create_nodes(graph.auto(), importData, labels={"Film"})
            exportedCount += len(rows)
            print(f"{exportedCount}/{totalCount} title records exported to Neo4j")
        except Exception as error:
            print(error)

    # Names
    # En vous basant sur ce qui a été fait dans la section précédente, exportez les données de la table tNames
    # A COMPLETER
    exportedCount = 0
    cursor.execute("SELECT COUNT(1) FROM tArtist")
    totalCount = cursor.fetchval()
    cursor.execute("SELECT idArtist, primaryName, birthYear FROM tArtist")
    while True:
        importData = []
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break

        i = 0
        for row in rows:
            # Créer un objet Node avec comme label Artist et les propriétés adéquates
            n = Node("Artist", idArtist=row[0], primaryName=row[1], birthYear=row[2])
            importData.append(n)
            i += 1

        try:
            create_nodes(graph.auto(), importData, labels={"Artist"})
            exportedCount += len(rows)
            print(f"{exportedCount}/{totalCount} title records exported to Neo4j")
        except Exception as error:
            print(error)

    try:
        print("Indexing Film nodes...")
        graph.run("CREATE INDEX IF NOT EXISTS FOR (f:Film) ON (f.idFilm)")
        print("Indexing Name (Artist) nodes...")
        graph.run("CREATE INDEX IF NOT EXISTS FOR (a:Artist) ON (a.idArtist)")
    except Exception as error:
        print(error)


    # Relationships
    exportedCount = 0
    cursor.execute("SELECT COUNT(1) FROM tJob")
    totalCount = cursor.fetchval()
    cursor.execute(f"SELECT idArtist, category, idFilm FROM tJob")

    while True:
        importData = { "acted in": [], "directed": [], "produced": [], "composed": [] }
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break

        for row in rows:
            relTuple=(row[0], {}, row[2])
            importData[row[1]].append(relTuple)

        try:
            for cat, relationships in importData.items():
                print(f"Processing relationships for category: {cat}")
                
                # Replace spaces with underscores for the relationship type
                relationship_type = cat.replace(" ", "_")
                if relationships: 
                    create_relationships(
                        graph.auto(), 
                        data=importData[cat], 
                        rel_type=relationship_type, 
                        start_node_key=("Artist", "idArtist"), 
                        end_node_key=("Film", "idFilm")
                        )

            exportedCount += len(rows)
            print(f"{exportedCount}/{totalCount} relationships exported to Neo4j")
        except Exception as error:
            print(error)
