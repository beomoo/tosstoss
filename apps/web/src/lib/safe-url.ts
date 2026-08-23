const SAFE_PROTOCOL = "https:";

export function toSafeHttpsUrl(value: string | null | undefined): string | null {
  if (value === null || value === undefined || value.length === 0) {
    return null;
  }

  try {
    const parsed = new URL(value);
    if (
      parsed.protocol !== SAFE_PROTOCOL ||
      parsed.username.length > 0 ||
      parsed.password.length > 0 ||
      parsed.hostname.length === 0
    ) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}
