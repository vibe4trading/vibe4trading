import { Helmet } from "react-helmet-async";

const BASE_URL = "https://vibe4trading.ai";
const DEFAULT_OG_IMAGE = `${BASE_URL}/og-image.png`;

interface SEOProps {
  title: string;
  description: string;
  canonicalPath?: string;
  ogImage?: string;
  ogType?: string;
  noindex?: boolean;
  children?: React.ReactNode;
}

export function SEO({
  title,
  description,
  canonicalPath,
  ogImage = DEFAULT_OG_IMAGE,
  ogType = "website",
  noindex = false,
  children,
}: SEOProps) {
  const fullTitle = `${title} | Vibe4Trading`;
  const canonicalUrl = canonicalPath ? `${BASE_URL}${canonicalPath}` : undefined;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />

      {noindex && <meta name="robots" content="noindex,nofollow" />}
      {!noindex && canonicalUrl && <link rel="canonical" href={canonicalUrl} />}

      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:type" content={ogType} />
      <meta property="og:site_name" content="Vibe4Trading" />
      {canonicalUrl && <meta property="og:url" content={canonicalUrl} />}

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImage} />

      {children}
    </Helmet>
  );
}
