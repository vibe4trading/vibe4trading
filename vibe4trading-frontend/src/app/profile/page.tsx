import { useState } from "react";
import { connect, signMessage } from "@joyid/evm";
import { useAuth } from "@/auth";
import { getApiBaseUrl } from "@/app/lib/v4t";

export default function ProfilePage() {
  const { user, refresh } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLink() {
    setPending(true);
    setError(null);

    try {
      const address = await connect();
      if (!address) throw new Error("Failed to connect wallet");

      const base = getApiBaseUrl();
      const challengeRes = await fetch(`${base}/auth/wallet/challenge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet_address: address }),
      });

      if (!challengeRes.ok) throw new Error("Failed to get challenge");
      const { nonce, message } = await challengeRes.json();

      const signature = await signMessage(message, address);
      if (!signature) throw new Error("Failed to sign message");

      const linkRes = await fetch(`${base}/me/link-wallet`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wallet_address: address, signature, nonce }),
      });

      if (!linkRes.ok) {
        const err = await linkRes.text();
        throw new Error(err || "Failed to link wallet");
      }

      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to link wallet");
    } finally {
      setPending(false);
    }
  }

  async function handleUnlink() {
    setPending(true);
    setError(null);

    try {
      const base = getApiBaseUrl();
      const res = await fetch(`${base}/me/unlink-wallet`, {
        method: "POST",
        credentials: "include",
      });

      if (!res.ok) throw new Error("Failed to unlink wallet");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink wallet");
    } finally {
      setPending(false);
    }
  }

  if (!user) {
    return <div className="container mx-auto p-8">Please sign in</div>;
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Profile</h1>
      
      <div className="mb-8">
        <h2 className="text-xl mb-2">Account</h2>
        <p className="text-gray-400">Email: {user.email || "N/A"}</p>
        <p className="text-gray-400">Display Name: {user.display_name || "N/A"}</p>
      </div>

      <div>
        <h2 className="text-xl mb-4">Wallet</h2>
        {user.wallet_address ? (
          <div>
            <p className="text-gray-400 mb-4">Address: {user.wallet_address}</p>
            <button
              type="button"
              className="waitlist"
              disabled={pending}
              onClick={handleUnlink}
            >
              {pending ? "Unlinking..." : "Unlink Wallet"}
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="waitlist"
            disabled={pending}
            onClick={handleLink}
          >
            {pending ? "Linking..." : "Link Wallet"}
          </button>
        )}
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>
    </div>
  );
}
