"use client";

// The Supports and Contradicts buttons on a claim page (sprint C.3, plan Part 3.3, ADR 0024): each opens one field for a
// paper's identifier, with a Cloudflare Turnstile check. Nothing else can be sent. Turnstile's script loads only once a
// visitor opens the form.

import Script from "next/script";
import { useEffect, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { canonicalIdentifier, MAX_LENGTH, NOT_AN_IDENTIFIER } from "@/lib/identifiers";

type Stance = "supports" | "contradicts";
const LABELS: Record<Stance, string> = { supports: "Supports", contradicts: "Contradicts" };

interface Turnstile {
  render(container: HTMLElement, options: Record<string, unknown>): string;
  reset(id: string): void;
  remove(id: string): void;
}

declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

type State = { kind: "idle" } | { kind: "sending" } | { kind: "done"; ok: boolean; message: string };

export function Evidence({ claimId, siteKey }: { claimId: string; siteKey: string }) {
  const [stance, setStance] = useState<Stance | null>(null);
  const [identifier, setIdentifier] = useState("");
  const [touched, setTouched] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<State>({ kind: "idle" });
  const widget = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const ids = { heading: useId(), form: useId(), input: useId(), hint: useId() };
  const open = stance !== null;
  const valid = canonicalIdentifier(identifier) !== null;
  const invalid = touched && identifier.trim() !== "" && !valid;

  useEffect(() => {
    const turnstile = window.turnstile;
    if (!open || !ready || !widget.current || !turnstile) return;
    const id = turnstile.render(widget.current, {
      sitekey: siteKey,
      action: "submit-evidence",
      size: "flexible",
      callback: (value: string) => setToken(value),
      "expired-callback": () => setToken(null),
      "error-callback": () => setToken(null),
    });
    widgetId.current = id;
    return () => {
      turnstile.remove(id);
      widgetId.current = null;
      setToken(null);
    };
  }, [open, ready, siteKey]);

  function choose(next: Stance) {
    setStance(stance === next ? null : next);
    setState({ kind: "idle" });
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (!stance || !token || !valid) return;
    setState({ kind: "sending" });
    let done: State;
    try {
      const response = await fetch("/api/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim: claimId, stance, identifier, token }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: string };
      done = { kind: "done", ok: response.status === 201, message: body.message ?? "Something went wrong. Please try again." };
    } catch {
      done = { kind: "done", ok: false, message: "The paper didn't reach us. Please check your connection and try again." };
    }
    setState(done);
    if (done.kind === "done" && done.ok) {
      setIdentifier("");
      setTouched(false);
      setStance(null);
    } else if (widgetId.current) {
      window.turnstile?.reset(widgetId.current); // a token works once
      setToken(null);
    }
  }

  return (
    <section aria-labelledby={ids.heading} className="space-y-3 rounded-lg border p-4">
      <h2 id={ids.heading} className="text-lg font-semibold">
        Know a paper about this claim?
      </h2>
      <p className="text-sm text-muted-foreground">
        Send its identifier. Triage checks the paper against the claim, and the claim changes only through a reviewed
        pull request.
      </p>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(LABELS) as Stance[]).map((s) => (
          <Button
            key={s}
            type="button"
            size="lg"
            className="h-11 min-w-28 px-4"
            variant={stance === s ? "default" : "outline"}
            aria-expanded={stance === s}
            aria-controls={stance === s ? ids.form : undefined}
            onClick={() => choose(s)}
          >
            {LABELS[s]}
          </Button>
        ))}
      </div>
      {stance && (
        <form id={ids.form} onSubmit={send} noValidate className="space-y-3">
          <Script
            src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
            strategy="afterInteractive"
            onReady={() => setReady(true)}
          />
          <label htmlFor={ids.input} className="block text-sm font-medium">
            A paper that {stance === "supports" ? "supports" : "contradicts"} this claim
          </label>
          <input
            id={ids.input}
            name="identifier"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            onBlur={() => setTouched(true)}
            maxLength={MAX_LENGTH}
            inputMode="url"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            placeholder="DOI, PubMed ID, PMC ID or arXiv ID, or a link to one"
            aria-invalid={invalid}
            aria-describedby={ids.hint}
            className="h-11 w-full min-w-0 rounded-lg border border-input bg-transparent px-3 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:bg-input/30"
          />
          <p id={ids.hint} className={invalid ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
            {invalid ? NOT_AN_IDENTIFIER : "No account and no comments: only the paper's identifier."}
          </p>
          <div ref={widget} className="min-h-16" />
          <div className="flex gap-2">
            <Button type="submit" size="lg" className="h-11 px-4" disabled={!token || !valid || state.kind === "sending"}>
              {state.kind === "sending" ? "Sending…" : "Send"}
            </Button>
            <Button type="button" variant="ghost" size="lg" className="h-11 px-4" onClick={() => setStance(null)}>
              Cancel
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Cloudflare Turnstile checks that you aren&apos;t a bot. To limit how often anyone can send, we keep a one-way
            hash of your network address for a day.
          </p>
        </form>
      )}
      <p role="status" className={state.kind === "done" && !state.ok ? "text-sm text-destructive" : "text-sm"}>
        {state.kind === "done" ? state.message : ""}
      </p>
    </section>
  );
}
