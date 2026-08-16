import type { components } from "@/types/api.generated";

type Schemas = components["schemas"];

// Application-facing names stay stable while api.generated.ts remains a pure,
// reproducible projection of contracts/openapi.json.
export type MissingReason = Schemas["MissingReason"];
export type AvailabilityStatus = Schemas["AvailabilityStatus"];
export type FreshnessStatus = Schemas["FreshnessStatus"];
export type FinalityStatus = Schemas["FinalityStatus"];
export type RevisionStatus = Schemas["RevisionStatus"];

export type HealthResponse = Schemas["HealthResponse"];
export type SafetyStatus = Schemas["SafetyStatus"];
export type SystemStatusResponse = Schemas["SystemStatusResponse"];
export type Issuer = Schemas["Issuer"];
export type Security = Schemas["Security"];
export type PriceBar = Schemas["PriceBar"];
export type DailyMarketFlow = Schemas["DailyMarketFlow"];
export type FinancialFact = Schemas["FinancialFact"];
export type InstitutionManager = Schemas["InstitutionManager"];
export type InstitutionHolding = Schemas["InstitutionHolding"];
export type InstitutionHoldingChange = Schemas["InstitutionHoldingChange"];
export type FilingDocument = Schemas["FilingDocument"];
export type FilingSentenceChange = Schemas["FilingSentenceChange"];
export type ValuationScenario = Schemas["ValuationScenario"];
export type Evidence = Schemas["Evidence"];
export type DataQualityStatus = Schemas["DataQualityStatus"];
export type CompanyOverview = Schemas["CompanyOverview"];
export type SecuritiesResponse = Schemas["SecuritiesResponse"];
export type CompanyOverviewResponse = Schemas["CompanyOverviewResponse"];
export type DataQualityResponse = Schemas["DataQualityResponse"];
