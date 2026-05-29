// drug_repurposing_explorer  (Cypher template)
//
// Finds drugs that might be repurposed for a disease: compounds approved for
// other conditions whose molecular targets are associated with this disease.
// Use when the user asks what existing drugs could potentially treat a disease.
//
// Parameters: $disease_name   (e.g. "breast cancer", "Alzheimer's disease")

MATCH (d:Disease) WHERE toLower(d.name) CONTAINS toLower($disease_name)
WITH d LIMIT 1

MATCH (d)<-[:ASSOCIATES_WITH]-(g:Gene)<-[:BINDS_GENE]-(c:Compound)
WHERE NOT (c)-[:TREATS]->(d) AND NOT (c)-[:PALLIATES]->(d)
WITH d, c, collect(DISTINCT g.name) AS connecting_genes

OPTIONAL MATCH (c)-[:TREATS]->(other:Disease)
WITH d, c, connecting_genes, collect(DISTINCT other.name)[0..3] AS currently_treats
OPTIONAL MATCH (c)<-[:INCLUDES]-(pc:PharmacologicClass)
RETURN
  d.name AS target_disease,
  c.name AS candidate_drug,
  connecting_genes[0..5] AS connecting_genes,
  currently_treats AS currently_approved_for,
  pc.name AS drug_class
ORDER BY size(connecting_genes) DESC
LIMIT 10
