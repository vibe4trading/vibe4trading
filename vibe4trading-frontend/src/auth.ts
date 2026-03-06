import NextAuth from "next-auth";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    {
      id: "v4t",
      name: "Vibe4Trading",
      type: "oidc",
      issuer: process.env.AUTH_AUTHENTIK_ISSUER,
      clientId: process.env.AUTH_AUTHENTIK_ID,
      clientSecret: process.env.AUTH_AUTHENTIK_SECRET,
      authorization: { params: { scope: "openid email profile groups" } },
    },
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.accessToken = account.access_token;
        token.accessTokenExpires =
          typeof account.expires_at === "number" ? account.expires_at * 1000 : undefined;
        token.refreshToken = account.refresh_token;
      }
      return token;
    },
    async session({ session }) {
      return session;
    },
  },
});
