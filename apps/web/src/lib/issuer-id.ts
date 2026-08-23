const ISSUER_ID_PATTERN = /^[a-z][a-z0-9_]{2,127}$/;

export function isValidIssuerId(value: string): boolean {
  return ISSUER_ID_PATTERN.test(value);
}
