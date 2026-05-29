// drug_profile_lookup  (Cypher template)
//
// Returns a full profile of one drug: what it treats, the genes it targets,
// the pathways those genes sit in, its side effects and its drug class.
// Use for "what does drug X do / target / cause" questions.
//
// Parameters: $drug_name

MATCH (c:Compound) WHERE toLower(c.name) CONTAINS toLower($drug_name)
WITH c LIMIT 1
OPTIONAL MATCH (c)-[:TREATS]->(d_treat:Disease)
OPTIONAL MATCH (c)-[:PALLIATES]->(d_pal:Disease)
OPTIONAL MATCH (c)-[:BINDS_GENE]->(g:Gene)
OPTIONAL MATCH (c)-[:CAUSES_SIDE_EFFECT]->(se:SideEffect)
OPTIONAL MATCH (c)-[:BINDS_GENE]->(:Gene)-[:PARTICIPATES_IN]->(pw:Pathway)
OPTIONAL MATCH (c)<-[:INCLUDES]-(pc:PharmacologicClass)
RETURN
  c.name AS drug_name,
  c.identifier AS drug_id,
  collect(DISTINCT d_treat.name)[0..8] AS treats,
  collect(DISTINCT d_pal.name)[0..5] AS palliates,
  collect(DISTINCT g.name)[0..8] AS molecular_targets,
  collect(DISTINCT se.name)[0..10] AS side_effects,
  collect(DISTINCT pw.name)[0..5] AS biological_pathways,
  pc.name AS drug_class
