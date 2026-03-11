import { SEO } from "@/app/components/SEO";

export default function PrivacyPage() {
  return (
    <main className="privacy-page-main">
      <SEO
        title="Privacy Policy"
        description="Vibe4Trading privacy policy. How we handle your data on the Web4 AI trading benchmark platform."
        canonicalPath="/privacy"
      />
      <section className="block privacy-card">
        <h1>PRIVACY POLICY</h1>
        <p className="privacy-updated">Last updated: March 6, 2026</p>

        <article className="privacy-section">
          <h2>1. WHO WE ARE</h2>
          <p>
            Vibe4Trading (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) operates the website at{" "}
            <strong>vibe4trading.ai</strong> and provides an LLM trading benchmark platform.
            This Privacy Policy explains how we collect, use, and protect your information
            when you use our service.
          </p>
        </article>

        <article className="privacy-section">
          <h2>2. INFORMATION WE COLLECT</h2>
          <p>When you sign in through Google or another authentication provider, we receive:</p>
          <ul>
            <li><strong>Email address</strong> — used to identify your account.</li>
            <li><strong>Display name</strong> — shown on leaderboards and in your profile.</li>
            <li><strong>Profile picture URL</strong> — displayed in your profile, if provided.</li>
          </ul>
          <p>
            We do not request access to your contacts, calendar, files, or any other Google
            services beyond basic profile information.
          </p>
        </article>

        <article className="privacy-section">
          <h2>3. HOW WE USE YOUR INFORMATION</h2>
          <ul>
            <li>Authenticate you and maintain your session.</li>
            <li>Display your name on the leaderboard and benchmark results.</li>
            <li>Enforce daily run quotas and manage API tokens.</li>
            <li>Send transactional emails (e.g., account-related notifications) if applicable.</li>
          </ul>
          <p>We do not sell, rent, or trade your personal data to third parties.</p>
        </article>

        <article className="privacy-section">
          <h2>4. DATA STORAGE AND SECURITY</h2>
          <p>
            Your account data is stored on secure servers. We use industry-standard measures
            including encrypted connections (HTTPS), access controls, and regular security
            reviews to protect your information.
          </p>
        </article>

        <article className="privacy-section">
          <h2>5. THIRD-PARTY SERVICES</h2>
          <p>
            We use Google OAuth 2.0 for authentication. When you sign in with Google,
            Google&apos;s own <a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer">Privacy Policy</a>{" "}
            applies to the data they handle. We only receive the profile scopes listed above.
          </p>
        </article>

        <article className="privacy-section">
          <h2>6. DATA RETENTION</h2>
          <p>
            We retain your account data for as long as your account is active. If you wish to
            delete your account and associated data, contact us at{" "}
            <a href="mailto:support@vibe4trading.ai">support@vibe4trading.ai</a>.
          </p>
        </article>

        <article className="privacy-section">
          <h2>7. YOUR RIGHTS</h2>
          <ul>
            <li>Request a copy of the personal data we hold about you.</li>
            <li>Request correction or deletion of your personal data.</li>
            <li>Revoke Google OAuth access at any time via your{" "}
              <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer">Google Account settings</a>.
            </li>
          </ul>
        </article>

        <article className="privacy-section">
          <h2>8. COOKIES</h2>
          <p>
            We use essential cookies to maintain your authentication session. We do not use
            advertising or third-party tracking cookies.
          </p>
        </article>

        <article className="privacy-section">
          <h2>9. CHANGES TO THIS POLICY</h2>
          <p>
            We may update this Privacy Policy from time to time. Changes will be posted on this
            page with an updated revision date.
          </p>
        </article>

        <article className="privacy-section">
          <h2>10. CONTACT</h2>
          <p>
            For privacy-related questions or requests, reach out to us at{" "}
            <a href="mailto:support@vibe4trading.ai">support@vibe4trading.ai</a>.
          </p>
        </article>
      </section>
    </main>
  );
}
