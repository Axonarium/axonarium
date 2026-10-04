// Cloudflare Turnstile, checked on the server: a widget's token is worth nothing until siteverify accepts it (ADR 0024).

export const SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify";
export const ACTION = "submit-evidence"; // set by the widget, so a token from another form on another site can't be reused
export const MAX_TOKEN = 2048; // Cloudflare's limit

/** Whether Cloudflare accepts a token. Fails closed: an error, a timeout or an unexpected answer is a no. */
export async function verifyTurnstile(
  token: string,
  secret: string,
  ip: string | null,
  fetcher: typeof fetch = fetch,
): Promise<boolean> {
  if (!token || token.length > MAX_TOKEN) return false;
  const body = new URLSearchParams({ secret, response: token });
  if (ip) body.set("remoteip", ip);
  try {
    const response = await fetcher(SITEVERIFY, { method: "POST", body, signal: AbortSignal.timeout(10_000) });
    if (!response.ok) return false;
    const answer = (await response.json()) as { success?: unknown; action?: unknown };
    // Cloudflare's test keys answer without an action; real widgets always carry the one they were given.
    return answer.success === true && (answer.action === undefined || answer.action === "" || answer.action === ACTION);
  } catch {
    return false;
  }
}
