// The read API's contract (OpenAPI 3.1), served at /api/v1/openapi.json. Responses are checked against these
// schemas in lib/api.test.ts (ADR 0013).

import type { OpenAPIV3_1 } from "openapi-types";

import { SITE } from "./sitemap";

// OpenAPI 3.1 marks a nullable value with a type array, which openapi-types only accepts through a cast.
const nullable = (...type: string[]) => ({ type: [...type, "null"] }) as OpenAPIV3_1.SchemaObject;
const ref = (name: string) => ({ $ref: `#/components/schemas/${name}` });
const page = (item: string) => ({
  type: "object",
  required: ["items", "limit", "offset", "total"],
  properties: {
    items: { type: "array", items: ref(item) },
    limit: { type: "integer" },
    offset: { type: "integer" },
    total: { type: "integer" },
  },
});
const json = (schema: object, description: string) => ({ description, content: { "application/json": { schema } } });
const errors = {
  "400": json(ref("Error"), "A query parameter is out of range"),
  "404": json(ref("Error"), "Nothing has that ID"),
  "503": json(ref("Error"), "The database couldn't be read"),
};
const paging: OpenAPIV3_1.ParameterObject[] = [
  { name: "limit", in: "query", schema: { type: "integer", minimum: 1, maximum: 200, default: 50 } },
  { name: "offset", in: "query", schema: { type: "integer", minimum: 0, default: 0 } },
];
const id = (description: string): OpenAPIV3_1.ParameterObject => ({
  name: "id",
  in: "path",
  required: true,
  description,
  schema: { type: "string" },
});

export const openapi: OpenAPIV3_1.Document = {
  openapi: "3.1.0",
  info: {
    title: "Axonarium read API",
    version: "1.0.0",
    description:
      "Read-only access to Axonarium's regions, connections, claims and sources. Every claim carries the terms " +
      "under which it may be reused: project-curated claims are CC BY 4.0; claims made from the Allen Mouse Brain " +
      "Connectivity Atlas keep the Allen Institute's terms (non-commercial use, with attribution).",
    license: { name: "Code: Apache-2.0; data: per claim, see `terms`", identifier: "Apache-2.0" },
  },
  servers: [{ url: `${SITE}/api/v1` }],
  paths: {
    "/regions": {
      get: {
        summary: "Atlas regions, by name or acronym",
        parameters: [
          { name: "q", in: "query", description: "Part of a name or acronym", schema: { type: "string", maxLength: 100 } },
          { name: "atlas", in: "query", schema: { type: "string" } },
          { name: "amygdala", in: "query", schema: { type: "boolean" } },
          ...paging,
        ],
        responses: { "200": json(page("Region"), "Regions, by ID"), "400": errors["400"], "503": errors["503"] },
      },
    },
    "/regions/{id}": {
      get: {
        summary: "A region with its subregions, outputs and inputs",
        parameters: [id("An atlas region ID, such as MBA:295")],
        responses: { "200": json(ref("RegionDetail"), "The region"), ...errors },
      },
    },
    "/connections": {
      get: {
        summary: "Connections, strongest projection density first",
        parameters: [
          { name: "subject", in: "query", description: "Region or neuron type ID", schema: { type: "string" } },
          { name: "object", in: "query", description: "Region or neuron type ID", schema: { type: "string" } },
          { name: "species", in: "query", description: "NCBITaxon ID", schema: { type: "string" } },
          { name: "predicate", in: "query", schema: { type: "string" } },
          { name: "min_density", in: "query", schema: { type: "number", minimum: 0 } },
          ...paging,
        ],
        responses: { "200": json(page("Connection"), "Connections"), "400": errors["400"], "503": errors["503"] },
      },
    },
    "/connections/{id}": {
      get: {
        summary: "A connection with every claim behind it",
        parameters: [id("subject|predicate|object|species, URL-encoded")],
        responses: { "200": json(ref("ConnectionDetail"), "The connection"), ...errors },
      },
    },
    "/claims/{id}": {
      get: {
        summary: "One claim",
        parameters: [id("A claim ID, such as clm-…")],
        responses: { "200": json(ref("Claim"), "The claim"), ...errors },
      },
    },
    "/sources/{id}": {
      get: {
        summary: "A cited source",
        parameters: [id("A source key, such as doi:10.1038/nature13186")],
        responses: { "200": json(ref("Source"), "The source"), ...errors },
      },
    },
  },
  components: {
    schemas: {
      Error: { type: "object", required: ["error"], properties: { error: { type: "string" } } },
      Terms: {
        type: "object",
        required: ["id", "name", "url"],
        properties: {
          id: { enum: ["cc-by-4.0", "allen-institute"] },
          name: { type: "string" },
          url: { type: "string", format: "uri" },
          note: { type: "string" },
        },
      },
      RegionRef: {
        type: "object",
        required: ["id", "acronym", "name"],
        properties: { id: { type: "string" }, acronym: nullable("string"), name: nullable("string") },
      },
      Region: {
        type: "object",
        required: ["id", "acronym", "name", "atlas", "parent", "uberon", "uberon_label", "amygdala"],
        properties: {
          id: { type: "string" },
          acronym: nullable("string"),
          name: { type: "string" },
          atlas: { type: "string" },
          parent: nullable("string"),
          uberon: nullable("string"),
          uberon_label: nullable("string"),
          amygdala: nullable("boolean"),
        },
      },
      Link: {
        type: "object",
        description: "One of a region's connections: the other region, the strongest density and the claim counts",
        required: ["connection", "region", "density", "claims", "accepted"],
        properties: {
          connection: { type: "string" },
          region: ref("RegionRef"),
          density: nullable("number"),
          claims: { type: "integer" },
          accepted: { type: "integer" },
        },
      },
      RegionDetail: {
        type: "object",
        required: ["region", "subregions", "outputs", "inputs"],
        properties: {
          region: ref("Region"),
          subregions: { type: "array", items: ref("RegionRef") },
          outputs: { type: "array", items: ref("Link") },
          inputs: { type: "array", items: ref("Link") },
        },
      },
      Connection: {
        type: "object",
        required: ["id", "subject", "predicate", "object", "species", "claims", "present", "absent", "density", "evidence_classes", "terms"],
        properties: {
          id: { type: "string" },
          subject: ref("RegionRef"),
          predicate: { type: "string" },
          object: ref("RegionRef"),
          species: { type: "string" },
          claims: { type: "integer" },
          present: { type: "integer" },
          absent: { type: "integer" },
          density: nullable("number"),
          evidence_classes: { type: "array", items: { type: "string" } },
          terms: { type: "array", items: { enum: ["cc-by-4.0", "allen-institute"] } },
        },
      },
      ConnectionDetail: {
        allOf: [ref("Connection"), { type: "object", required: ["claims_detail"], properties: { claims_detail: { type: "array", items: ref("Claim") } } }],
      },
      Claim: {
        type: "object",
        required: ["id", "subject", "predicate", "object", "species", "evidence_class", "result", "sign", "citation", "paraphrase", "curation", "status", "terms"],
        properties: {
          id: { type: "string" },
          subject: ref("Entity"),
          predicate: { type: "string" },
          object: ref("Entity"),
          species: { type: "string" },
          evidence_class: { type: "string" },
          result: { type: "string" },
          sign: { type: "string" },
          strength: nullable("string"),
          measurements: { ...nullable("array"), items: { type: "object" } } as OpenAPIV3_1.SchemaObject,
          citation: ref("Citation"),
          paraphrase: { type: "string" },
          excerpt: nullable("string"),
          curation: { type: "object" },
          verification: nullable("object"),
          status: { type: "string" },
          extra: nullable("object"),
          terms: ref("Terms"),
        },
      },
      Entity: {
        type: "object",
        required: ["type", "id", "atlas"],
        properties: { type: { type: "string" }, id: { type: "string" }, atlas: nullable("string") },
      },
      Citation: {
        type: "object",
        required: ["source", "locator"],
        properties: {
          source: { type: "string", description: "The source's key; see /sources/{id}" },
          doi: nullable("string"),
          pmid: nullable("string"),
          pmcid: nullable("string"),
          arxiv: nullable("string"),
          locator: { type: "string" },
        },
      },
      Source: {
        type: "object",
        required: ["id", "title", "year", "journal", "kind", "license", "open_access", "retracted"],
        properties: {
          id: { type: "string" },
          title: nullable("string"),
          year: nullable("integer"),
          journal: { ...nullable("string"), description: "The journal, or a preprint's server" },
          kind: {
            type: "string",
            enum: ["journal_article", "preprint", "dataset", "other"],
            description: "The kind of publication, from its registry. Preprints are a lower evidence tier than published work.",
          },
          license: nullable("string"),
          open_access: nullable("boolean"),
          retracted: nullable("boolean"),
        },
      },
    },
  },
};
