// drug_interaction_checker  (Cypher template)
//
// Explains how two drugs may interact by finding the molecular targets and
// biological pathways they share. Use when the user asks about combining two
// named drugs or about the safety of a combination.
//
// Parameters: $drug1_name, $drug2_name

MATCH (c1:Compound) WHERE toLower(c1.name) CONTAINS toLower($drug1_name)
MATCH (c2:Compound) WHERE toLower(c2.name) CONTAINS toLower($drug2_name)
WITH c1, c2 LIMIT 1

OPTIONAL MATCH (c1)-[:BINDS_GENE]->(g:Gene)<-[:BINDS_GENE]-(c2)
WITH c1, c2, collect(DISTINCT g.name) AS shared_targets

OPTIONAL MATCH (c1)-[:BINDS_GENE]->(:Gene)-[:PARTICIPATES_IN]->(pw:Pathway)
              <-[:PARTICIPATES_IN]-(:Gene)<-[:BINDS_GENE]-(c2)
RETURN
  c1.name AS drug1,
  c2.name AS drug2,
  shared_targets AS shared_molecular_targets,
  collect(DISTINCT pw.name)[0..5] AS shared_pathways
