import { SEO } from "@/app/components/SEO";
import { usePrerenderReady } from "@/app/hooks/usePrerenderReady";
import { Helmet } from "react-helmet-async";
import { useTranslation } from "react-i18next";

export default function ContactPage() {
  const { t } = useTranslation();
  usePrerenderReady(true);

  return (
    <main className="contact-page-main">
      <SEO
        title={t("meta.contact.title")}
        description={t("meta.contact.description")}
        canonicalPath="/contact"
      />
      <Helmet>
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "ContactPage",
          "name": "Contact Vibe4Trading",
          "url": "https://vibe4trading.ai/contact",
          "description": "Get in touch with the Vibe4Trading team for partnerships, support, or feedback.",
          "mainEntity": {
            "@type": "Organization",
            "name": "Vibe4Trading",
            "email": "info@vibe4trading.ai",
            "url": "https://vibe4trading.ai",
            "sameAs": ["https://x.com/vibe4trading"]
          }
        })}</script>
      </Helmet>
      <section className="block contact-card">
        <h1>CONTACT US</h1>
        <p>For partnerships, technical support, or product feedback, reach out through the channels below.</p>

        <div className="contact-grid">
          <article className="contact-item">
            <span>Business</span>
            <strong>info@vibe4trading.ai</strong>
            <a className="contact-link" href="mailto:info@vibe4trading.ai">SEND EMAIL</a>
          </article>
          <article className="contact-item">
            <span>Support</span>
            <strong>support@vibe4trading.ai</strong>
            <a className="contact-link" href="mailto:support@vibe4trading.ai">OPEN TICKET</a>
          </article>
          <article className="contact-item">
            <span>Community</span>
            <strong>@vibe4trading</strong>
            <a className="contact-link" href="https://x.com/vibe4trading" target="_blank" rel="noreferrer">VISIT X</a>
          </article>
        </div>
      </section>
    </main>
  );
}
