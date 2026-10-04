// The server's side of submissions: the secret keys, the submitter's hash and the call to submit_evidence() (ADR 0024).
import "server-only";

import { createClient } from "@supabase/supabase-js";

import { getClaim } from "./data";
import { clientHash, type Inserted, type Stance, type SubmitDeps } from "./submit";
import { verifyTurnstile } from "./turnstile";

interface Config {
  url: string;
  secretKey: string;
  turnstileSecret: string;
}

/** Submissions are open only once the maintainer has set all three keys; until then the buttons stay hidden. */
export function inboxConfig(): Config | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const secretKey = process.env.SUPABASE_SECRET_KEY;
  const turnstileSecret = process.env.TURNSTILE_SECRET_KEY;
  return url && secretKey && turnstileSecret && process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY
    ? { url, secretKey, turnstileSecret }
    : null;
}

export function inboxDeps(config: Config, address: string | null): SubmitDeps {
  const db = createClient(config.url, config.secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
  return {
    verify: (token) => verifyTurnstile(token, config.turnstileSecret, address),
    claimStatus: async (id) => {
      const claim = await getClaim(id);
      return claim === undefined || claim === null ? claim : claim.status;
    },
    insert: async (claim: string, stance: Stance, identifier: string) => {
      const { data, error } = await db.rpc("submit_evidence", {
        p_claim: claim,
        p_stance: stance,
        p_identifier: identifier,
        p_client: clientHash(address, config.turnstileSecret),
      });
      if (error) throw new Error(error.message);
      return data as Inserted;
    },
  };
}
