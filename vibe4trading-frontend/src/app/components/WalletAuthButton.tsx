import { useState } from "react";
import { connect, signMessage } from "@joyid/evm";
import { useAuth } from "@/auth";

interface ChallengeResponse {
  nonce: string;
  message: string;
}

interface VerifyResponse {
  user_id: string;
  wallet_address: string;
}

export function WalletAuthButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { refresh } = useAuth();

  async function handleSignIn() {
    setPending(true);
    setError(null);

    try {
      // Step 1: Connect wallet
      const address = await connect();
      if (!address) {
        throw new Error("Failed to connect wallet");
      }

      // Step 2: Get challenge
      const challengeRes = await fetch("/api/auth/wallet/challenge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet_address: address }),
      });

      if (!challengeRes.ok) {
        throw new Error("Failed to get challenge");
      }

      const challenge: ChallengeResponse = await challengeRes.json();

      // Step 3: Sign message
      const signature = await signMessage(challenge.message, address);
      if (!signature) {
        throw new Error("Failed to sign message");
      }

      // Step 4: Verify signature
      const verifyRes = await fetch("/api/auth/wallet/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wallet_address: address,
          signature,
          nonce: challenge.nonce,
        }),
      });

      if (!verifyRes.ok) {
        throw new Error("Signature verification failed");
      }

      const result: VerifyResponse = await verifyRes.json();

      // Step 5: Refresh auth state
      await refresh();
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        className="waitlist"
        disabled={pending}
        onClick={handleSignIn}
      >
        {pending ? "Connecting..." : "Sign in with JoyID"}
      </button>
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  );
}
