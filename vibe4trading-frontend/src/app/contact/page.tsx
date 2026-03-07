export default function ContactPage() {
  return (
    <main className="contact-page-main">
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
