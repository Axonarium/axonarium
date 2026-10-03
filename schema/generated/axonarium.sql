CREATE TYPE "ConnectivityPredicate" AS ENUM ('projects_to', 'synapses_onto', 'functionally_connects_to');
CREATE TYPE "EvidenceClass" AS ENUM ('anterograde_tracer', 'retrograde_tracer', 'single_neuron_reconstruction', 'electron_microscopy', 'transsynaptic_tracer', 'optogenetic_circuit_mapping', 'paired_recording', 'electrical_stimulation');
CREATE TYPE "Result" AS ENUM ('present', 'absent', 'ambiguous');
CREATE TYPE "Sign" AS ENUM ('excitatory', 'inhibitory', 'modulatory', 'unknown');
CREATE TYPE "OrdinalStrength" AS ENUM ('weak', 'moderate', 'strong');
CREATE TYPE "ClaimStatus" AS ENUM ('proposed', 'accepted', 'disputed', 'retracted');
CREATE TYPE "Correspondence" AS ENUM ('equivalent', 'partial');
CREATE TYPE "Confidence" AS ENUM ('high', 'medium', 'low');
CREATE TYPE "EntityType" AS ENUM ('region', 'neuron_type');
CREATE TYPE "Actor" AS ENUM ('human', 'agent');
CREATE TYPE "Role" AS ENUM ('curator', 'ingester', 'extractor', 'verifier', 'reconciler', 'triage');
CREATE TYPE "Verdict" AS ENUM ('agree', 'disagree', 'unsure');
CREATE TYPE "QuantityKind" AS ENUM ('connection_probability', 'synapse_count', 'conduction_delay', 'projection_density', 'fraction_of_labelled_neurons');
CREATE TYPE "Transmitter" AS ENUM ('glutamate', 'gaba', 'acetylcholine', 'dopamine', 'serotonin', 'noradrenaline', 'neuropeptide', 'unknown');
CREATE TYPE "HomologyBasis" AS ENUM ('connectivity', 'gene_expression', 'cytoarchitecture', 'development', 'function', 'expert_assertion');

CREATE TABLE "Any" (
	id SERIAL NOT NULL,
	PRIMARY KEY (id)
);
COMMENT ON TABLE "Any" IS 'Any JSON value. Used for the open-ended extra map.';

CREATE TABLE "EntityRef" (
	uid SERIAL NOT NULL,
	type "EntityType" NOT NULL,
	id TEXT NOT NULL,
	atlas TEXT,
	PRIMARY KEY (uid)
);
COMMENT ON TABLE "EntityRef" IS 'A reference to a region or neuron type, used as the subject or object of a claim.';
COMMENT ON COLUMN "EntityRef".type IS 'Whether the reference is to a region or a neuron type.';
COMMENT ON COLUMN "EntityRef".id IS 'The entity''s ID: an atlas region (MBA, HBA), a UBERON term, a project neuron type (nt-...) or a Cell Ontology term.';
COMMENT ON COLUMN "EntityRef".atlas IS 'The pinned atlas version an atlas region belongs to, such as allen-mouse-ccf-2017. Required for MBA and HBA IDs.';

CREATE TABLE "Citation" (
	id SERIAL NOT NULL,
	doi TEXT,
	pmid TEXT,
	pmcid TEXT,
	arxiv TEXT,
	locator TEXT NOT NULL,
	PRIMARY KEY (id)
);
COMMENT ON TABLE "Citation" IS 'Where a claim''s evidence is: one paper or preprint, and the figure, table or section within it.';
COMMENT ON COLUMN "Citation".doi IS 'The paper''s DOI, without the https://doi.org/ prefix.';
COMMENT ON COLUMN "Citation".pmid IS 'The paper''s PubMed ID. Quote it in YAML.';
COMMENT ON COLUMN "Citation".pmcid IS 'The paper''s PubMed Central ID, such as PMC1234567.';
COMMENT ON COLUMN "Citation".arxiv IS 'The preprint''s arXiv ID, such as 2409.13740.';
COMMENT ON COLUMN "Citation".locator IS 'Where in the source the evidence is, such as "Fig. 3B".';

CREATE TABLE "Curation" (
	id SERIAL NOT NULL,
	by "Actor" NOT NULL,
	orcid TEXT,
	role "Role" NOT NULL,
	model TEXT,
	prompt TEXT,
	date DATE NOT NULL,
	PRIMARY KEY (id)
);
COMMENT ON TABLE "Curation" IS 'Who drafted or curated a claim, and how.';
COMMENT ON COLUMN "Curation".by IS 'Whether a human or an agent did the work.';
COMMENT ON COLUMN "Curation".orcid IS 'The human''s ORCID iD, without the https://orcid.org/ prefix.';
COMMENT ON COLUMN "Curation".role IS 'The role the human or agent acted in.';
COMMENT ON COLUMN "Curation".model IS 'The model ID an agent ran on, such as claude-opus-5-5.';
COMMENT ON COLUMN "Curation".prompt IS 'The versioned role prompt an agent ran, such as extract@1.0.0.';
COMMENT ON COLUMN "Curation".date IS 'When the work was done. Quote it in YAML.';

CREATE TABLE "Verification" (
	id SERIAL NOT NULL,
	by "Actor" NOT NULL,
	orcid TEXT,
	role "Role" NOT NULL,
	model TEXT,
	prompt TEXT,
	verdict "Verdict" NOT NULL,
	date DATE NOT NULL,
	PRIMARY KEY (id)
);
COMMENT ON TABLE "Verification" IS 'An independent check of a claim against its source.';
COMMENT ON COLUMN "Verification".by IS 'Whether a human or an agent did the work.';
COMMENT ON COLUMN "Verification".orcid IS 'The human''s ORCID iD, without the https://orcid.org/ prefix.';
COMMENT ON COLUMN "Verification".role IS 'The role the human or agent acted in.';
COMMENT ON COLUMN "Verification".model IS 'The model ID an agent ran on, such as claude-opus-5-5.';
COMMENT ON COLUMN "Verification".prompt IS 'The versioned role prompt an agent ran, such as extract@1.0.0.';
COMMENT ON COLUMN "Verification".verdict IS 'Whether the verifier agrees with the claim.';
COMMENT ON COLUMN "Verification".date IS 'When the work was done. Quote it in YAML.';

CREATE TABLE "KnowledgeBase" (
	id SERIAL NOT NULL,
	PRIMARY KEY (id)
);
COMMENT ON TABLE "KnowledgeBase" IS 'Every record in one container, as written to dumps. Files in data/ hold one record each.';

CREATE TABLE "ConnectivityClaim" (
	predicate "ConnectivityPredicate" NOT NULL,
	species TEXT NOT NULL,
	evidence_class "EvidenceClass" NOT NULL,
	result "Result" NOT NULL,
	sign "Sign" NOT NULL,
	strength "OrdinalStrength",
	id TEXT NOT NULL,
	paraphrase TEXT NOT NULL,
	excerpt TEXT,
	status "ClaimStatus" NOT NULL,
	"KnowledgeBase_id" INTEGER,
	subject_uid INTEGER NOT NULL,
	object_uid INTEGER NOT NULL,
	source_id INTEGER NOT NULL,
	curation_id INTEGER NOT NULL,
	verification_id INTEGER,
	extra_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY("KnowledgeBase_id") REFERENCES "KnowledgeBase" (id),
	FOREIGN KEY(subject_uid) REFERENCES "EntityRef" (uid),
	FOREIGN KEY(object_uid) REFERENCES "EntityRef" (uid),
	FOREIGN KEY(source_id) REFERENCES "Citation" (id),
	FOREIGN KEY(curation_id) REFERENCES "Curation" (id),
	FOREIGN KEY(verification_id) REFERENCES "Verification" (id),
	FOREIGN KEY(extra_id) REFERENCES "Any" (id)
);
COMMENT ON TABLE "ConnectivityClaim" IS 'A claim that a region or neuron type connects to another in one species, shown by one kind of evidence. Edges are computed from these claims at build time and are never edited by hand.';
COMMENT ON COLUMN "ConnectivityClaim".predicate IS 'The kind of connection claimed.';
COMMENT ON COLUMN "ConnectivityClaim".species IS 'The organism, as an NCBI Taxonomy ID such as NCBITaxon:10090.';
COMMENT ON COLUMN "ConnectivityClaim".evidence_class IS 'The method that produced the evidence.';
COMMENT ON COLUMN "ConnectivityClaim".result IS 'What the evidence showed. "absent" means tested and not found, which is different from no claim at all.';
COMMENT ON COLUMN "ConnectivityClaim".sign IS 'The effect of the connection. Required, so that "unknown" is stated deliberately.';
COMMENT ON COLUMN "ConnectivityClaim".strength IS 'The connection''s strength on an ordinal scale, if reported.';
COMMENT ON COLUMN "ConnectivityClaim".id IS 'The record''s identifier.';
COMMENT ON COLUMN "ConnectivityClaim".paraphrase IS 'The evidence summarised in the curator''s own words. Copyright-safe: verbatim text belongs in excerpt, and only from openly licensed papers.';
COMMENT ON COLUMN "ConnectivityClaim".excerpt IS 'A short verbatim quotation, at most 300 characters, taken only from an openly licensed paper.';
COMMENT ON COLUMN "ConnectivityClaim".status IS 'Where the claim is in its life cycle.';
COMMENT ON COLUMN "ConnectivityClaim"."KnowledgeBase_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "ConnectivityClaim".subject_uid IS 'The region or neuron type the relationship starts from.';
COMMENT ON COLUMN "ConnectivityClaim".object_uid IS 'The region or neuron type the relationship ends at.';
COMMENT ON COLUMN "ConnectivityClaim".source_id IS 'Where the evidence for the claim is.';
COMMENT ON COLUMN "ConnectivityClaim".curation_id IS 'Who drafted or curated the claim.';
COMMENT ON COLUMN "ConnectivityClaim".verification_id IS 'The independent check of the claim, if one was made.';
COMMENT ON COLUMN "ConnectivityClaim".extra_id IS 'Open-ended map of namespaced keys (prefix.name, such as lab.tracer) to any JSON value. Core facts always have typed fields and never live only here.';

CREATE TABLE "HomologyClaim" (
	subject_species TEXT NOT NULL,
	object_species TEXT NOT NULL,
	correspondence "Correspondence" NOT NULL,
	confidence "Confidence" NOT NULL,
	id TEXT NOT NULL,
	paraphrase TEXT NOT NULL,
	excerpt TEXT,
	status "ClaimStatus" NOT NULL,
	"KnowledgeBase_id" INTEGER,
	subject_uid INTEGER NOT NULL,
	object_uid INTEGER NOT NULL,
	source_id INTEGER NOT NULL,
	curation_id INTEGER NOT NULL,
	verification_id INTEGER,
	extra_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY("KnowledgeBase_id") REFERENCES "KnowledgeBase" (id),
	FOREIGN KEY(subject_uid) REFERENCES "EntityRef" (uid),
	FOREIGN KEY(object_uid) REFERENCES "EntityRef" (uid),
	FOREIGN KEY(source_id) REFERENCES "Citation" (id),
	FOREIGN KEY(curation_id) REFERENCES "Curation" (id),
	FOREIGN KEY(verification_id) REFERENCES "Verification" (id),
	FOREIGN KEY(extra_id) REFERENCES "Any" (id)
);
COMMENT ON TABLE "HomologyClaim" IS 'A claim that a region or neuron type in one species corresponds to one in another. Homology is a weighted, cited claim, never a merge of nodes.';
COMMENT ON COLUMN "HomologyClaim".subject_species IS 'The organism of the homology claim''s subject.';
COMMENT ON COLUMN "HomologyClaim".object_species IS 'The organism of the homology claim''s object.';
COMMENT ON COLUMN "HomologyClaim".correspondence IS 'How fully the two entities correspond.';
COMMENT ON COLUMN "HomologyClaim".confidence IS 'How strong the evidence for the correspondence is.';
COMMENT ON COLUMN "HomologyClaim".id IS 'The record''s identifier.';
COMMENT ON COLUMN "HomologyClaim".paraphrase IS 'The evidence summarised in the curator''s own words. Copyright-safe: verbatim text belongs in excerpt, and only from openly licensed papers.';
COMMENT ON COLUMN "HomologyClaim".excerpt IS 'A short verbatim quotation, at most 300 characters, taken only from an openly licensed paper.';
COMMENT ON COLUMN "HomologyClaim".status IS 'Where the claim is in its life cycle.';
COMMENT ON COLUMN "HomologyClaim"."KnowledgeBase_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "HomologyClaim".subject_uid IS 'The region or neuron type the relationship starts from.';
COMMENT ON COLUMN "HomologyClaim".object_uid IS 'The region or neuron type the relationship ends at.';
COMMENT ON COLUMN "HomologyClaim".source_id IS 'Where the evidence for the claim is.';
COMMENT ON COLUMN "HomologyClaim".curation_id IS 'Who drafted or curated the claim.';
COMMENT ON COLUMN "HomologyClaim".verification_id IS 'The independent check of the claim, if one was made.';
COMMENT ON COLUMN "HomologyClaim".extra_id IS 'Open-ended map of namespaced keys (prefix.name, such as lab.tracer) to any JSON value. Core facts always have typed fields and never live only here.';

CREATE TABLE "Atlas" (
	id TEXT NOT NULL,
	name TEXT NOT NULL,
	species TEXT NOT NULL,
	version TEXT NOT NULL,
	url TEXT,
	brainglobe_name TEXT,
	"KnowledgeBase_id" INTEGER,
	extra_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY("KnowledgeBase_id") REFERENCES "KnowledgeBase" (id),
	FOREIGN KEY(extra_id) REFERENCES "Any" (id)
);
COMMENT ON TABLE "Atlas" IS 'A specific, pinned version of a reference atlas. An atlas update creates a new record and a mapping file, never silent ID changes.';
COMMENT ON COLUMN "Atlas".id IS 'The record''s identifier.';
COMMENT ON COLUMN "Atlas".name IS 'The entity''s full name.';
COMMENT ON COLUMN "Atlas".species IS 'The organism, as an NCBI Taxonomy ID such as NCBITaxon:10090.';
COMMENT ON COLUMN "Atlas".version IS 'The atlas version, as its authors name it.';
COMMENT ON COLUMN "Atlas".url IS 'Where the atlas is published.';
COMMENT ON COLUMN "Atlas".brainglobe_name IS 'The atlas''s name in the BrainGlobe Atlas API, such as allen_mouse_25um.';
COMMENT ON COLUMN "Atlas"."KnowledgeBase_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "Atlas".extra_id IS 'Open-ended map of namespaced keys (prefix.name, such as lab.tracer) to any JSON value. Core facts always have typed fields and never live only here.';

CREATE TABLE "NeuronType" (
	id TEXT NOT NULL,
	name TEXT NOT NULL,
	species TEXT NOT NULL,
	transmitter "Transmitter",
	cell_ontology TEXT,
	"KnowledgeBase_id" INTEGER,
	region_uid INTEGER NOT NULL,
	extra_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY("KnowledgeBase_id") REFERENCES "KnowledgeBase" (id),
	FOREIGN KEY(region_uid) REFERENCES "EntityRef" (uid),
	FOREIGN KEY(extra_id) REFERENCES "Any" (id)
);
COMMENT ON TABLE "NeuronType" IS 'A population of neurons with a shared location, transmitter and markers. Mapped to the Cell Ontology where a term exists.';
COMMENT ON COLUMN "NeuronType".id IS 'The record''s identifier.';
COMMENT ON COLUMN "NeuronType".name IS 'The entity''s full name.';
COMMENT ON COLUMN "NeuronType".species IS 'The organism, as an NCBI Taxonomy ID such as NCBITaxon:10090.';
COMMENT ON COLUMN "NeuronType".transmitter IS 'The neuron type''s main neurotransmitter.';
COMMENT ON COLUMN "NeuronType".cell_ontology IS 'The matching Cell Ontology term.';
COMMENT ON COLUMN "NeuronType"."KnowledgeBase_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "NeuronType".region_uid IS 'Where the neuron type''s cell bodies are.';
COMMENT ON COLUMN "NeuronType".extra_id IS 'Open-ended map of namespaced keys (prefix.name, such as lab.tracer) to any JSON value. Core facts always have typed fields and never live only here.';

CREATE TABLE "Source" (
	id TEXT NOT NULL,
	title TEXT,
	year INTEGER,
	journal TEXT,
	license TEXT,
	open_access BOOLEAN,
	retracted BOOLEAN,
	"KnowledgeBase_id" INTEGER,
	extra_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY("KnowledgeBase_id") REFERENCES "KnowledgeBase" (id),
	FOREIGN KEY(extra_id) REFERENCES "Any" (id)
);
COMMENT ON TABLE "Source" IS 'Cached metadata for a paper or preprint that claims cite. Filled from Crossref and PubMed in Phase 1.';
COMMENT ON COLUMN "Source".id IS 'The record''s identifier.';
COMMENT ON COLUMN "Source".title IS 'The paper''s title.';
COMMENT ON COLUMN "Source".year IS 'The year of publication.';
COMMENT ON COLUMN "Source".journal IS 'The journal or preprint server.';
COMMENT ON COLUMN "Source".license IS 'The paper''s licence, as an SPDX ID where one exists.';
COMMENT ON COLUMN "Source".open_access IS 'Whether the full text is openly available.';
COMMENT ON COLUMN "Source".retracted IS 'Whether the paper has been retracted, per Crossref.';
COMMENT ON COLUMN "Source"."KnowledgeBase_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "Source".extra_id IS 'Open-ended map of namespaced keys (prefix.name, such as lab.tracer) to any JSON value. Core facts always have typed fields and never live only here.';

CREATE TABLE "Measurement" (
	id SERIAL NOT NULL,
	quantity "QuantityKind" NOT NULL,
	value FLOAT NOT NULL,
	unit TEXT NOT NULL,
	sd FLOAT,
	sem FLOAT,
	ci_low FLOAT,
	ci_high FLOAT,
	n INTEGER,
	"ConnectivityClaim_id" TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY("ConnectivityClaim_id") REFERENCES "ConnectivityClaim" (id)
);
COMMENT ON TABLE "Measurement" IS 'A quantity reported for a connection, with its unit and uncertainty. A missing field means unknown; nothing has a default.';
COMMENT ON COLUMN "Measurement".quantity IS 'What was measured.';
COMMENT ON COLUMN "Measurement".value IS 'The measured value, in unit.';
COMMENT ON COLUMN "Measurement".unit IS 'The UCUM unit code, such as ms, or "1" for a dimensionless value.';
COMMENT ON COLUMN "Measurement".sd IS 'Standard deviation.';
COMMENT ON COLUMN "Measurement".sem IS 'Standard error of the mean.';
COMMENT ON COLUMN "Measurement".ci_low IS 'Lower bound of the 95%% confidence interval.';
COMMENT ON COLUMN "Measurement".ci_high IS 'Upper bound of the 95%% confidence interval.';
COMMENT ON COLUMN "Measurement".n IS 'Sample size behind the measurement.';
COMMENT ON COLUMN "Measurement"."ConnectivityClaim_id" IS 'Autocreated FK slot';

CREATE TABLE "Region" (
	id TEXT NOT NULL,
	name TEXT NOT NULL,
	acronym TEXT,
	atlas TEXT NOT NULL,
	parent TEXT,
	uberon TEXT,
	"KnowledgeBase_id" INTEGER,
	extra_id INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY(atlas) REFERENCES "Atlas" (id),
	FOREIGN KEY(parent) REFERENCES "Region" (id),
	FOREIGN KEY("KnowledgeBase_id") REFERENCES "KnowledgeBase" (id),
	FOREIGN KEY(extra_id) REFERENCES "Any" (id)
);
COMMENT ON TABLE "Region" IS 'A structure as defined in one pinned atlas version, mapped to UBERON.';
COMMENT ON COLUMN "Region".id IS 'The record''s identifier.';
COMMENT ON COLUMN "Region".name IS 'The entity''s full name.';
COMMENT ON COLUMN "Region".acronym IS 'The region''s acronym in its atlas.';
COMMENT ON COLUMN "Region".atlas IS 'The pinned atlas version the region belongs to.';
COMMENT ON COLUMN "Region".parent IS 'The region one level up in the atlas hierarchy.';
COMMENT ON COLUMN "Region".uberon IS 'The matching UBERON term.';
COMMENT ON COLUMN "Region"."KnowledgeBase_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "Region".extra_id IS 'Open-ended map of namespaced keys (prefix.name, such as lab.tracer) to any JSON value. Core facts always have typed fields and never live only here.';

CREATE TABLE "HomologyClaim_basis" (
	"HomologyClaim_id" TEXT,
	basis "HomologyBasis" NOT NULL,
	PRIMARY KEY ("HomologyClaim_id", basis),
	FOREIGN KEY("HomologyClaim_id") REFERENCES "HomologyClaim" (id)
);
COMMENT ON TABLE "HomologyClaim_basis" IS 'None';
COMMENT ON COLUMN "HomologyClaim_basis"."HomologyClaim_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "HomologyClaim_basis".basis IS 'The kinds of evidence the correspondence rests on.';

CREATE TABLE "NeuronType_markers" (
	"NeuronType_id" TEXT,
	markers TEXT,
	PRIMARY KEY ("NeuronType_id", markers),
	FOREIGN KEY("NeuronType_id") REFERENCES "NeuronType" (id)
);
COMMENT ON TABLE "NeuronType_markers" IS 'None';
COMMENT ON COLUMN "NeuronType_markers"."NeuronType_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "NeuronType_markers".markers IS 'Gene symbols that identify the neuron type, such as Sst.';

CREATE TABLE "NeuronType_synonyms" (
	"NeuronType_id" TEXT,
	synonyms TEXT,
	PRIMARY KEY ("NeuronType_id", synonyms),
	FOREIGN KEY("NeuronType_id") REFERENCES "NeuronType" (id)
);
COMMENT ON TABLE "NeuronType_synonyms" IS 'None';
COMMENT ON COLUMN "NeuronType_synonyms"."NeuronType_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "NeuronType_synonyms".synonyms IS 'Other names for the entity.';

CREATE TABLE "Region_synonyms" (
	"Region_id" TEXT,
	synonyms TEXT,
	PRIMARY KEY ("Region_id", synonyms),
	FOREIGN KEY("Region_id") REFERENCES "Region" (id)
);
COMMENT ON TABLE "Region_synonyms" IS 'None';
COMMENT ON COLUMN "Region_synonyms"."Region_id" IS 'Autocreated FK slot';
COMMENT ON COLUMN "Region_synonyms".synonyms IS 'Other names for the entity.';

