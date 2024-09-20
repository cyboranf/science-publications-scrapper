from neo4j import GraphDatabase

driver = GraphDatabase.driver('neo4j://localhost:7687',
                              auth=('neo4j', '12345678'))
driver.session().run("match (n)-[r]->(n1) delete r, n, n1")
driver.session().run("match (n) delete n")
driver.close()
print("Done")